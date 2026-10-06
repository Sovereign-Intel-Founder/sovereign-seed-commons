#ifndef SIP_ENVELOPE_H
#define SIP_ENVELOPE_H

#include <stdint.h>
#include <stddef.h>
#include <net/if.h>
#include <linux/if_link.h>
#include <xdp/xsk.h>
#include <xdp/libxdp.h>

typedef struct {
    char ifname[IFNAMSIZ];
    uint32_t queue_id;
    void *umem_area;
    struct xsk_umem *umem;
    struct xsk_ring_prod fill;
    struct xsk_ring_cons comp;
    struct xsk_socket *xsk_sock;
    struct xsk_ring_cons rx;
    struct xsk_ring_prod tx;
    int xsk_fd;
} sip_xsk_handle_t;

// Correct signature: 2 arguments, returns handle pointer
sip_xsk_handle_t *sip_xsk_create_ring(const char *ifname, uint32_t queue_id);
void *sip_xsk_poll_ingress(void *arg);

#endif // SIP_ENVELOPE_H
