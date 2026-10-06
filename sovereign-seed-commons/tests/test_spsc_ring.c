#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>
#include "../include/sip_mesh/sip_spsc_ring.h"

#define QUEUE_CAPACITY 1048576

typedef struct {
    uint64_t seq;
    uint64_t timestamp;
} test_payload_t;

typedef struct {
    sip_spsc_ring_t *ring;
    uint64_t total_events;
    int core_id;
} thread_arg_t;

static void *producer_thread(void *arg) {
    thread_arg_t *targs = (thread_arg_t *)arg;
    
    // Pin thread to core
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(targs->core_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    for (uint64_t i = 0; i < targs->total_events; i++) {
        test_payload_t item = { .seq = i, .timestamp = (uint64_t)clock() };
        while (!sip_spsc_push(targs->ring, &item)) {
            // Spin-wait when ring is full
            __builtin_ia32_pause();
        }
    }
    return NULL;
}

static void *consumer_thread(void *arg) {
    thread_arg_t *targs = (thread_arg_t *)arg;
    
    // Pin thread to adjacent core
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(targs->core_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    uint64_t received = 0;
    test_payload_t item;

    while (received < targs->total_events) {
        if (sip_spsc_pop(targs->ring, &item)) {
            received++;
        } else {
            __builtin_ia32_pause();
        }
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    uint64_t events = 12800000;
    if (argc > 2) {
        events = strtoull(argv[2], NULL, 10);
    }

    size_t ring_bytes = sizeof(test_payload_t) * QUEUE_CAPACITY;
    void *memory = aligned_alloc(64, ring_bytes);
    if (!memory) {
        perror("Failed to allocate aligned memory");
        return 1;
    }

    sip_spsc_ring_t ring;
    sip_spsc_init(&ring, memory, QUEUE_CAPACITY, sizeof(test_payload_t));

    pthread_t prod, cons;
    thread_arg_t prod_args = { .ring = &ring, .total_events = events, .core_id = 2 };
    thread_arg_t cons_args = { .ring = &ring, .total_events = events, .core_id = 3 };

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    pthread_create(&prod, NULL, producer_thread, &prod_args);
    pthread_create(&cons, NULL, consumer_thread, &cons_args);

    pthread_join(prod, NULL);
    pthread_join(cons, NULL);

    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("Processed %lu events in %.4f seconds (%.2f ops/sec)\n", events, elapsed, events / elapsed);

    free(memory);
    return 0;
}
