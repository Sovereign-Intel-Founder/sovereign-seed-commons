#ifndef SIP_XSK_H
#define SIP_XSK_H

#define _GNU_SOURCE
#include <stdint.h>
#include <linux/if_xdp.h>

typedef struct {
    int xsk_fd;
    void *umem_area;
    void *rx_map;
    void *tx_map;
    void *fill_map;
    void *comp_map;
    struct xdp_mmap_offsets off;
    uint32_t queue_id;
} sip_xsk_handle_t;

sip_xsk_handle_t *sip_xsk_create_ring(const char *ifname, uint32_t queue_id);
int sip_xsk_poll_ingress(sip_xsk_handle_t *xsk, void (*packet_handler)(const uint8_t *pkt, uint32_t len));

#endif
