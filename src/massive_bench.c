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

#define QUEUE_SIZE 262144 // Must be a power of 2
#define QUEUE_MASK (QUEUE_SIZE - 1)
#define NUM_PRODUCERS 32
#define EVENTS_PER_PRODUCER 500000
#define LOG_FILE "logs/massive_benchmark.jsonl"

typedef struct {
    long long timestamp_ns;
    long sequence;
    int producer_id;
    char msg[64];
} LogEventPayload;

typedef struct {
    _Alignas(64) atomic_size_t sequence;
    LogEventPayload data;
} QueueCell;

typedef struct {
    QueueCell items[QUEUE_SIZE];
    _Alignas(64) atomic_size_t head;
    _Alignas(64) atomic_size_t tail;
    _Alignas(64) atomic_int running;
} MPMCQueue;

static MPMCQueue queue;
static pthread_t producer_threads[NUM_PRODUCERS];
static pthread_t logger_thread;

void init_queue(MPMCQueue* q) {
    atomic_store(&q->head, 0);
    atomic_store(&q->tail, 0);
    atomic_store(&q->running, 1);
    for (size_t i = 0; i < QUEUE_SIZE; i++) {
        atomic_store_explicit(&q->items[i].sequence, i, memory_order_relaxed);
    }
}

int mpmc_enqueue(MPMCQueue* q, LogEventPayload data) {
    QueueCell* cell;
    size_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    for (;;) {
        cell = &q->items[pos & QUEUE_MASK];
        size_t seq = atomic_load_explicit(&cell->sequence, memory_order_acquire);
        intptr_t dif = (intptr_t)seq - (intptr_t)pos;
        if (dif == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->tail, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) {
                break;
            }
        } else if (dif < 0) {
            sched_yield();
            pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
        } else {
            pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
        }
    }
    cell->data = data;
    atomic_store_explicit(&cell->sequence, pos + 1, memory_order_release);
    return 1;
}

int mpmc_dequeue(MPMCQueue* q, LogEventPayload* data) {
    size_t pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    QueueCell* cell;
    for (;;) {
        cell = &q->items[pos & QUEUE_MASK];
        size_t seq = atomic_load_explicit(&cell->sequence, memory_order_acquire);
        intptr_t dif = (intptr_t)seq - (intptr_t)(pos + 1);
        if (dif == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->head, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) {
                break;
            }
        } else if (dif < 0) {
            return 0;
        } else {
            pos = atomic_load_explicit(&q->head, memory_order_relaxed);
        }
    }
    *data = cell->data;
    atomic_store_explicit(&cell->sequence, pos + QUEUE_SIZE, memory_order_release);
    return 1;
}

void* logger_worker(void* arg) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(64, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    FILE* f = fopen(LOG_FILE, "w");
    if (!f) return NULL;
    char buf[524288];
    setvbuf(f, buf, _IOFBF, sizeof(buf));

    size_t total_target = (size_t)NUM_PRODUCERS * EVENTS_PER_PRODUCER;
    size_t processed = 0;
    LogEventPayload ev;

    while (processed < total_target) {
        if (mpmc_dequeue(&queue, &ev)) {
            fprintf(f, "{\"ts\": %lld, \"p\": %d, \"seq\": %ld}\n", ev.timestamp_ns, ev.producer_id, ev.sequence);
            processed++;
        } else {
            if (!atomic_load_explicit(&queue.running, memory_order_acquire)) break;
            sched_yield();
        }
    }
    fclose(f);
    return NULL;
}

void* producer_worker(void* arg) {
    long pid = (long)arg;
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(pid % 64, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    for (long i = 0; i < EVENTS_PER_PRODUCER; i++) {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        long long ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;

        LogEventPayload ev = {ns, i, (int)pid, "Load test"};
        mpmc_enqueue(&queue, ev);
    }
    return NULL;
}

int main() {
    mkdir("logs", 0755);
    init_queue(&queue);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start);

    pthread_create(&logger_thread, NULL, logger_worker, NULL);
    for (long i = 0; i < NUM_PRODUCERS; i++) {
        pthread_create(&producer_threads[i], NULL, producer_worker, (void*)i);
    }

    for (long i = 0; i < NUM_PRODUCERS; i++) {
        pthread_join(producer_threads[i], NULL);
    }

    size_t total_target = (size_t)NUM_PRODUCERS * EVENTS_PER_PRODUCER;
    while (atomic_load_explicit(&queue.head, memory_order_relaxed) < total_target) {
        usleep(100);
    }

    atomic_store_explicit(&queue.running, 0, memory_order_release);
    pthread_join(logger_thread, NULL);

    clock_gettime(CLOCK_MONOTONIC_RAW, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    long total = (long)NUM_PRODUCERS * EVENTS_PER_PRODUCER;
    printf("MASSIVE_BENCHMARK_SUCCESS: Processed %ld events across %d threads in %.4f sec => %.2f events/sec\n", 
           total, NUM_PRODUCERS, elapsed, total / elapsed);
    return 0;
}
