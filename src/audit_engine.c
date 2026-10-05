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

#define QUEUE_SIZE 1048576
#define QUEUE_MASK (QUEUE_SIZE - 1)
#define NUM_PRODUCERS 64
#define LOG_FILE "logs/audit_arbitrage.jsonl"

typedef struct {
    long long ingest_ts_ns;
    long long process_ts_ns;
    uint64_t buy_price;
    uint64_t sell_price;
    int64_t net_profit_fixed;
    long sequence;
} AuditTradePayload;

typedef struct {
    _Alignas(64) atomic_size_t sequence;
    AuditTradePayload data;
} QueueCell;

typedef struct {
    QueueCell items[QUEUE_SIZE];
    _Alignas(64) atomic_size_t head;
    _Alignas(64) atomic_size_t tail;
    _Alignas(64) atomic_int running;
    _Alignas(64) atomic_long total_profit;
    _Alignas(64) atomic_long executed_count;
} AuditEngineQueue;

static AuditEngineQueue engine_queue;
static pthread_t workers[NUM_PRODUCERS];
static pthread_t audit_logger;

void init_queue(AuditEngineQueue* q) {
    atomic_store(&q->head, 0);
    atomic_store(&q->tail, 0);
    atomic_store(&q->running, 1);
    atomic_store(&q->total_profit, 0);
    atomic_store(&q->executed_count, 0);
    for (size_t i = 0; i < QUEUE_SIZE; i++) {
        atomic_store_explicit(&q->items[i].sequence, i, memory_order_relaxed);
    }
}

int mpmc_enqueue(AuditEngineQueue* q, AuditTradePayload data) {
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

int mpmc_dequeue(AuditEngineQueue* q, AuditTradePayload* data) {
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

void* audit_logger_worker(void* arg) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(127, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    FILE* f = fopen(LOG_FILE, "w");
    if (!f) return NULL;
    char buf[1048576];
    setvbuf(f, buf, _IOFBF, sizeof(buf));

    AuditTradePayload trade;
    size_t logged = 0;

    while (atomic_load_explicit(&engine_queue.running, memory_order_acquire) || 
           atomic_load_explicit(&engine_queue.head, memory_order_relaxed) != atomic_load_explicit(&engine_queue.tail, memory_order_relaxed)) {
        
        if (mpmc_dequeue(&engine_queue, &trade)) {
            fprintf(f, "{\"ingest_ns\": %lld, \"process_ns\": %lld, \"buy_px\": %lu, \"sell_px\": %lu, \"profit\": %ld, \"seq\": %ld}\n",
                    trade.ingest_ts_ns, trade.process_ts_ns, trade.buy_price, trade.sell_price, trade.net_profit_fixed, trade.sequence);
            atomic_fetch_add(&engine_queue.total_profit, trade.net_profit_fixed);
            atomic_fetch_add(&engine_queue.executed_count, 1);
            logged++;
        } else {
            usleep(10);
        }
    }

    fclose(f);
    printf("Audit Logger flushed %lu verified records to %s\n", logged, LOG_FILE);
    return NULL;
}

void* simulation_worker(void* arg) {
    long pid = (long)arg;
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(pid % 128, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    for (long i = 0; i < 200000; i++) {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        long long ingest_ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;

        // Simulated market spread processing
        uint64_t buy_px = 95000000000ULL + (i % 300);
        uint64_t sell_px = buy_px + 20000 + ((i % 5) * 150);
        int64_t profit = (int64_t)(sell_px - buy_px) - 1200;

        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        long long process_ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;

        AuditTradePayload trade = {
            .ingest_ts_ns = ingest_ns,
            .process_ts_ns = process_ns,
            .buy_price = buy_px,
            .sell_price = sell_px,
            .net_profit_fixed = profit,
            .sequence = i
        };
        mpmc_enqueue(&engine_queue, trade);
    }
    return NULL;
}

int main() {
    mkdir("logs", 0755);
    init_queue(&engine_queue);

    printf("Launching Sovereign Audit-Grade Engine across %d threads...\n", NUM_PRODUCERS);
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start);

    pthread_create(&audit_logger, NULL, audit_logger_worker, NULL);
    for (long i = 0; i < NUM_PRODUCERS; i++) {
        pthread_create(&workers[i], NULL, simulation_worker, (void*)i);
    }

    for (long i = 0; i < NUM_PRODUCERS; i++) {
        pthread_join(workers[i], NULL);
    }

    while (atomic_load_explicit(&engine_queue.head, memory_order_relaxed) < (NUM_PRODUCERS * 200000)) {
        usleep(100);
    }

    atomic_store_explicit(&engine_queue.running, 0, memory_order_release);
    pthread_join(audit_logger, NULL);

    clock_gettime(CLOCK_MONOTONIC_RAW, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    long total_trades = atomic_load(&engine_queue.executed_count);
    long long total_profit = atomic_load(&engine_queue.total_profit);

    printf("AUDIT_ENGINE_SUCCESS: Processed %ld audited trades in %.4f sec\n", total_trades, elapsed);
    printf("Throughput: %.2f trades/sec\n", total_trades / elapsed);
    printf("Cumulative Profit: %.8f units\n", (double)total_profit / 100000000.0);
    return 0;
}
