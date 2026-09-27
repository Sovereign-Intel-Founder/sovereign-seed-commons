#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stdatomic.h>
#include <stdalign.h>
#include <sched.h>

#define QUEUE_SIZE 1048576 // 1M slot power-of-2 ring buffer
#define QUEUE_MASK (QUEUE_SIZE - 1)
#define NUM_PRODUCERS 64
#define LOG_FILE "logs/sovereign_master.jsonl"

typedef struct {
    long long timestamp_ns;
    uint64_t venue_id;
    uint64_t price_fixed; // Scaled by 10^8
    int64_t spread_delta;
    long sequence;
} MarketTickPayload;

typedef struct {
    _Alignas(64) atomic_size_t sequence;
    MarketTickPayload data;
} QueueCell;

typedef struct {
    QueueCell items[QUEUE_SIZE];
    _Alignas(64) atomic_size_t head;
    _Alignas(64) atomic_size_t tail;
    _Alignas(64) atomic_int running;
} MasterMPMCQueue;

static MasterMPMCQueue master_queue;
static pthread_t ingestion_threads[NUM_PRODUCERS];
static pthread_t logger_thread;

void init_master_queue(MasterMPMCQueue* q) {
    atomic_store(&q->head, 0);
    atomic_store(&q->tail, 0);
    atomic_store(&q->running, 1);
    for (size_t i = 0; i < QUEUE_SIZE; i++) {
        atomic_store_explicit(&q->items[i].sequence, i, memory_order_relaxed);
    }
}

int mpmc_enqueue(MasterMPMCQueue* q, MarketTickPayload data) {
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

int mpmc_dequeue(MasterMPMCQueue* q, MarketTickPayload* data) {
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

void* master_logger_worker(void* arg) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(127, &cpuset); // Dedicate highest core to telemetry output
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    FILE* f = fopen(LOG_FILE, "w");
    if (!f) return NULL;
    char buf[1048576];
    setvbuf(f, buf, _IOFBF, sizeof(buf));

    MarketTickPayload tick;
    size_t logged_count = 0;

    while (atomic_load_explicit(&master_queue.running, memory_order_acquire) || 
           atomic_load_explicit(&master_queue.head, memory_order_relaxed) != atomic_load_explicit(&master_queue.tail, memory_order_relaxed)) {
        
        if (mpmc_dequeue(&master_queue, &tick)) {
            fprintf(f, "{\"ts_ns\": %lld, \"venue\": %lu, \"price\": %lu, \"spread\": %ld, \"seq\": %ld}\n",
                    tick.timestamp_ns, tick.venue_id, tick.price_fixed, tick.spread_delta, tick.sequence);
            logged_count++;
        } else {
            usleep(10);
        }
    }

    fclose(f);
    printf("Master Logger flushed %lu records to %s\n", logged_count, LOG_FILE);
    return NULL;
}

void* ingestion_worker(void* arg) {
    long pid = (long)arg;
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(pid % 128, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    // Simulate high-frequency feed input stream per thread
    for (long i = 0; i < 200000; i++) {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        long long ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;

        MarketTickPayload tick = {
            .timestamp_ns = ns,
            .venue_id = (uint64_t)(pid + 1),
            .price_fixed = 95000000000ULL + (i % 1000),
            .spread_delta = 1250 + (i % 50),
            .sequence = i
        };
        mpmc_enqueue(&master_queue, tick);
    }
    return NULL;
}

int main() {
    mkdir("logs", 0755);
    init_master_queue(&master_queue);

    printf("Starting Sovereign Master Engine across %d threads...\n", NUM_PRODUCERS);
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start);

    pthread_create(&logger_thread, NULL, master_logger_worker, NULL);
    for (long i = 0; i < NUM_PRODUCERS; i++) {
        pthread_create(&ingestion_threads[i], NULL, ingestion_worker, (void*)i);
    }

    for (long i = 0; i < NUM_PRODUCERS; i++) {
        pthread_join(ingestion_threads[i], NULL);
    }

    // Allow logger to finish draining queue
    while (atomic_load_explicit(&master_queue.head, memory_order_relaxed) < (NUM_PRODUCERS * 200000)) {
        usleep(100);
    }

    atomic_store_explicit(&master_queue.running, 0, memory_order_release);
    pthread_join(logger_thread, NULL);

    clock_gettime(CLOCK_MONOTONIC_RAW, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    long total_events = (long)NUM_PRODUCERS * 200000;
    
    printf("SOVEREIGN_MASTER_SUCCESS: Processed %ld events in %.4f sec => %.2f events/sec\n",
           total_events, elapsed, total_events / elapsed);
    return 0;
}
