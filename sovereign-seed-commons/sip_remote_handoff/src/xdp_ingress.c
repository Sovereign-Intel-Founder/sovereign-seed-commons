#include "../include/sip_envelope.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#include <xdp/xsk.h>
#include <xdp/libxdp.h>
#include <string.h>
#include <sys/mman.h>
#include <netinet/ip.h>
#include <netinet/ether.h>
#include <arpa/inet.h>

void *sip_xsk_poll_ingress(void *arg) {
    sip_xsk_handle_t *xsk = (sip_xsk_handle_t *)arg;
    
    // Rigorous pointer validation to prevent segmentation faults from unmapped rings
    if (__builtin_expect(!xsk || xsk->rx.ring == NULL || xsk->rx.ring == MAP_FAILED ||
                         xsk->fill.ring == NULL || xsk->fill.ring == MAP_FAILED, 0)) {
        fprintf(stderr, "[SIP_CRITICAL] Ingress polling thread aborted: Invalid handle or unmapped ring structure (rx.ring=%p, fill.ring=%p).\n", 
                xsk ? xsk->rx.ring : NULL, xsk ? xsk->fill.ring : NULL);
        return NULL;
    }

    printf("[SIP_EXEC] Sovereign Ingress Engine online: Zero-copy polling active on %s [Queue %u, FD: %d]\n", 
           xsk->ifname, xsk->queue_id, xsk->xsk_fd);

    uint64_t total_packets_processed = 0;
    uint64_t total_bytes_ingested = 0;

    // Main low-latency ring polling loop
    while (1) {
        uint32_t rcvd;
        uint32_t idx_rx = 0;

        rcvd = xsk_ring_cons__peek(&xsk->rx, 64, &idx_rx);
        if (__builtin_expect(!rcvd, 0)) {
            usleep(2);
            continue;
        }

        // Process incoming batch of zero-copy frames
        for (uint32_t i = 0; i < rcvd; i++) {
            const struct xdp_desc *desc = xsk_ring_cons__rx_desc(&xsk->rx, idx_rx + i);
            uint64_t addr = desc->addr;
            uint32_t len = desc->len;

            void *pkt_data = xsk_umem__get_data(xsk->umem_area, addr);
            
            if (__builtin_expect(pkt_data != NULL && len >= sizeof(struct ether_header), 1)) {
                total_packets_processed++;
                total_bytes_ingested += len;

                struct ether_header *eth = (struct ether_header *)pkt_data;
                uint16_t eth_type = ntohs(eth->ether_type);

                if (__builtin_expect(total_packets_processed % 100000 == 0, 0)) {
                    printf("[SIP_TELEMETRY] Ingested %lu packets (%lu total bytes), Last EtherType: 0x%04x, Len: %u\n", 
                           total_packets_processed, total_bytes_ingested, eth_type, len);
                }
            }
        }

        // Release consumed descriptors back to kernel RX ring
        xsk_ring_cons__release(&xsk->rx, rcvd);

        // Replenish Fill Ring with partial reservation handling
        uint32_t filled = 0;
        while (filled < rcvd) {
            uint32_t idx_fill = 0;
            uint32_t ret = xsk_ring_prod__reserve(&xsk->fill, rcvd - filled, &idx_fill);
            
            if (__builtin_expect(ret > 0, 1)) {
                for (uint32_t i = 0; i < ret; i++) {
                    const struct xdp_desc *desc = xsk_ring_cons__rx_desc(&xsk->rx, idx_rx + filled + i);
                    *xsk_ring_prod__fill_addr(&xsk->fill, idx_fill + i) = desc->addr;
                }
                xsk_ring_prod__submit(&xsk->fill, ret);
                filled += ret;
            } else {
                usleep(1);
            }
        }
    }

    return NULL;
}
