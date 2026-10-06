#ifndef SIP_COMMONS_BRIDGE_H
#define SIP_COMMONS_BRIDGE_H

#include <stdint.h>
#include <stdatomic.h>

#define SHM_NAME "/sip_commons_ring_v1"
#define RING_BUFFER_SIZE 65536
#define RING_MASK (RING_BUFFER_SIZE - 1)
#define PAYLOAD_MAX_LEN 1500

typedef struct {
    uint64_t trace_id;
    uint64_t timestamp_ns;
    uint32_t payload_len;
    uint8_t data[PAYLOAD_MAX_LEN];
} __attribute__((aligned(64))) sip_event_t;

typedef struct {
    atomic_uint_fast64_t head;
    atomic_uint_fast64_t tail;
    sip_event_t events[RING_BUFFER_SIZE];
} __attribute__((aligned(64))) sip_shm_ring_t;

#endif
