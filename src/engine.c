#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stdatomic.h>
#include <stdalign.h>
#include <sched.h>
#include <signal.h>

#define QUEUE_SIZE 131072
#define LOG_FILE "logs/sovereign.jsonl"
#define BATCH_FLUSH_COUNT 512

typedef struct {
    long long timestamp_ns;
    long sequence;
    char level[16];
    char msg[128];
} LogEventPayload;

typedef struct {
    LogEventPayload items[QUEUE_SIZE];
    _Alignas(64) atomic_size_t head;
    _Alignas(64) atomic_size_t tail;
    _Alignas(64) atomic_int running;
    _Alignas(64) atomic_flag lock;
} LogQueue;

static LogQueue log_queue;
static pthread_t logger_thread;
static volatile sig_atomic_t keep_running = 1;

void handle_shutdown(int sig) {
    (void)sig;
    keep_running = 0;
    atomic_store_explicit(&log_queue.running, 0, memory_order_release);
}

void* logger_worker(void* arg) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(1, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    // Apply real-time scheduling priority if permitted
    struct sched_param param;
    param.sched_priority = 20;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);

    FILE* f = fopen(LOG_FILE, "a");
    if (!f) {
        perror("Failed to open log file");
        return NULL;
    }

    char file_buffer[131072];
    setvbuf(f, file_buffer, _IOFBF, sizeof(file_buffer));

    size_t unflushed_count = 0;

    while (atomic_load_explicit(&log_queue.running, memory_order_acquire) || 
           atomic_load_explicit(&log_queue.head, memory_order_relaxed) != atomic_load_explicit(&log_queue.tail, memory_order_relaxed)) {
        
        size_t h = atomic_load_explicit(&log_queue.head, memory_order_relaxed);
        size_t t = atomic_load_explicit(&log_queue.tail, memory_order_acquire);

        if (h == t) {
            sched_yield();
            continue;
        }

        LogEventPayload event = log_queue.items[h & (QUEUE_SIZE - 1)];
        atomic_store_explicit(&log_queue.head, h + 1, memory_order_release);

        // Async JSON serialization offloaded entirely to background worker thread
        fprintf(f, "{\"timestamp_ns\": %lld, \"%s\": \"%s\", \"sequence\": %ld}\n", 
                event.timestamp_ns, event.level, event.msg, event.sequence);
        unflushed_count++;

        if (unflushed_count >= BATCH_FLUSH_COUNT) {
            fflush(f);
            unflushed_count = 0;
        }
    }

    fflush(f);
    fclose(f);
    return NULL;
}

void log_event(const char* level, const char* msg, long sequence) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    long long timestamp_ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;

    while (atomic_flag_test_and_set_explicit(&log_queue.lock, memory_order_acquire)) {
        __builtin_ia32_pause();
    }

    size_t t = atomic_load_explicit(&log_queue.tail, memory_order_relaxed);
    size_t h = atomic_load_explicit(&log_queue.head, memory_order_acquire);

    if ((t - h) < QUEUE_SIZE) {
        LogEventPayload* item = &log_queue.items[t & (QUEUE_SIZE - 1)];
        item->timestamp_ns = timestamp_ns;
        item->sequence = sequence;
        snprintf(item->level, sizeof(item->level), "%s", level);
        snprintf(item->msg, sizeof(item->msg), "%s", msg);
        
        atomic_store_explicit(&log_queue.tail, t + 1, memory_order_release);
    }

    atomic_flag_clear_explicit(&log_queue.lock, memory_order_release);
}

int main() {
    mkdir("logs", 0755);

    signal(SIGINT, handle_shutdown);
    signal(SIGTERM, handle_shutdown);

    atomic_store(&log_queue.head, 0);
    atomic_store(&log_queue.tail, 0);
    atomic_store(&log_queue.running, 1);
    atomic_flag_clear(&log_queue.lock);

    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(0, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    pthread_create(&logger_thread, NULL, logger_worker, NULL);

    log_event("INFO", "Sovereign Intelligence Protocol C engine initialized with async binary serialization", 0);

    long counter = 0;
    while (keep_running) {
        counter++;
        log_event("DEBUG", "Hardened telemetry heartbeat pulse", counter);
        usleep(100); 
    }

    atomic_store_explicit(&log_queue.running, 0, memory_order_release);
    pthread_join(logger_thread, NULL);

    return 0;
}
