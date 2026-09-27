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

#define QUEUE_SIZE 131072
#define LOG_FILE "logs/live_benchmark.jsonl"
#define BATCH_FLUSH_COUNT 4096
#define TOTAL_EVENTS 5000000

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

void* logger_worker(void* arg) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(1, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    struct sched_param param;
    param.sched_priority = 20;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);

    FILE* f = fopen(LOG_FILE, "w");
    if (!f) return NULL;

    char file_buffer[262144];
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

int main() {
    mkdir("logs", 0755);
    atomic_store(&log_queue.head, 0);
    atomic_store(&log_queue.tail, 0);
    atomic_store(&log_queue.running, 1);
    atomic_flag_clear(&log_queue.lock);

    pthread_create(&logger_thread, NULL, logger_worker, NULL);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start);

    for (long i = 1; i <= TOTAL_EVENTS; i++) {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        long long ts_ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;

        while (atomic_flag_test_and_set_explicit(&log_queue.lock, memory_order_acquire)) {
            __builtin_ia32_pause();
        }

        size_t t = atomic_load_explicit(&log_queue.tail, memory_order_relaxed);
        size_t h = atomic_load_explicit(&log_queue.head, memory_order_acquire);

        while ((t - h) >= QUEUE_SIZE) {
            atomic_flag_clear_explicit(&log_queue.lock, memory_order_release);
            sched_yield();
            while (atomic_flag_test_and_set_explicit(&log_queue.lock, memory_order_acquire)) {
                __builtin_ia32_pause();
            }
            t = atomic_load_explicit(&log_queue.tail, memory_order_relaxed);
            h = atomic_load_explicit(&log_queue.head, memory_order_acquire);
        }

        LogEventPayload* item = &log_queue.items[t & (QUEUE_SIZE - 1)];
        item->timestamp_ns = ts_ns;
        item->sequence = i;
        memcpy(item->level, "DEBUG", 6);
        memcpy(item->msg, "Arbitrage ring buffer saturation tick", 38);

        atomic_store_explicit(&log_queue.tail, t + 1, memory_order_release);
        atomic_flag_clear_explicit(&log_queue.lock, memory_order_release);
    }

    while (atomic_load_explicit(&log_queue.head, memory_order_relaxed) != atomic_load_explicit(&log_queue.tail, memory_order_relaxed)) {
        usleep(50);
    }

    clock_gettime(CLOCK_MONOTONIC_RAW, &end);
    atomic_store_explicit(&log_queue.running, 0, memory_order_release);
    pthread_join(logger_thread, NULL);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("LIVE_BENCHMARK_RESULTS: Processed %d events in %.4f seconds => %.2f events/sec\n", 
           TOTAL_EVENTS, elapsed, TOTAL_EVENTS / elapsed);

    return 0;
}
