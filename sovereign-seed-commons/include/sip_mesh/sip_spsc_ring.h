#ifndef SIP_SPSC_RING_H
#define SIP_SPSC_RING_H

#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#define SIP_CACHE_LINE_SIZE 64

typedef struct {
    size_t capacity;
    size_t element_size;
    uint8_t *storage;
    
    _Alignas(SIP_CACHE_LINE_SIZE) atomic_size_t head;
    _Alignas(SIP_CACHE_LINE_SIZE) atomic_size_t tail;
} sip_spsc_ring_t;

static inline void sip_spsc_init(sip_spsc_ring_t *ring, void *memory, size_t capacity, size_t element_size) {
    ring->capacity = capacity;
    ring->element_size = element_size;
    ring->storage = (uint8_t *)memory;
    atomic_init(&ring->head, 0);
    atomic_init(&ring->tail, 0);
}

static inline bool sip_spsc_push(sip_spsc_ring_t *ring, const void *data) {
    size_t current_tail = atomic_load_explicit(&ring->tail, memory_order_relaxed);
    size_t current_head = atomic_load_explicit(&ring->head, memory_order_acquire);

    if ((current_tail - current_head) >= ring->capacity) {
        return false;
    }

    size_t index = current_tail % ring->capacity;
    __builtin_memcpy(ring->storage + (index * ring->element_size), data, ring->element_size);

    atomic_store_explicit(&ring->tail, current_tail + 1, memory_order_release);
    return true;
}

static inline bool sip_spsc_pop(sip_spsc_ring_t *ring, void *out_data) {
    size_t current_head = atomic_load_explicit(&ring->head, memory_order_relaxed);
    size_t current_tail = atomic_load_explicit(&ring->tail, memory_order_acquire);

    if (current_head == current_tail) {
        return false;
    }

    size_t index = current_head % ring->capacity;
    __builtin_memcpy(out_data, ring->storage + (index * ring->element_size), ring->element_size);

    atomic_store_explicit(&ring->head, current_head + 1, memory_order_release);
    return true;
}

#endif // SIP_SPSC_RING_H
