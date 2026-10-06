#include "../include/sip_envelope.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <net/if.h>
#include <sys/socket.h>
#include <linux/if_link.h>
#include <xdp/xsk.h>
#include <xdp/libxdp.h>

#define UMEM_FRAME_SIZE XSK_UMEM__DEFAULT_FRAME_SIZE
#define UMEM_FRAMES     4096
#define UMEM_AREA_SIZE  (UMEM_FRAME_SIZE * UMEM_FRAMES)

sip_xsk_handle_t *sip_xsk_create_ring(const char *ifname, uint32_t queue_id) {
    if (!ifname) {
        fprintf(stderr, "[SIP_ERROR] Invalid interface name passed to sip_xsk_create_ring\n");
        return NULL;
    }

    sip_xsk_handle_t *xsk = malloc(sizeof(sip_xsk_handle_t));
    if (!xsk) {
        fprintf(stderr, "[SIP_ERROR] Failed to allocate memory for sip_xsk_handle_t\n");
        return NULL;
    }

    memset(xsk, 0, sizeof(sip_xsk_handle_t));
    strncpy(xsk->ifname, ifname, sizeof(xsk->ifname) - 1);
    xsk->queue_id = queue_id;

    int ret = posix_memalign(&xsk->umem_area, getpagesize(), UMEM_AREA_SIZE);
    if (ret != 0 || !xsk->umem_area) {
        fprintf(stderr, "[SIP_ERROR] Failed to allocate aligned UMEM area\n");
        free(xsk);
        return NULL;
    }

    struct xsk_umem_config umem_cfg = {
        .fill_size = XSK_RING_PROD__DEFAULT_NUM_DESCS,
        .comp_size = XSK_RING_CONS__DEFAULT_NUM_DESCS,
        .frame_size = UMEM_FRAME_SIZE,
        .frame_headroom = 0,
        .flags = 0
    };

    ret = xsk_umem__create(&xsk->umem, xsk->umem_area, UMEM_AREA_SIZE, &xsk->fill, &xsk->comp, &umem_cfg);
    if (ret != 0) {
        fprintf(stderr, "[SIP_ERROR] xsk_umem__create failed: %d (%s)\n", ret, strerror(-ret));
        free(xsk->umem_area);
        free(xsk);
        return NULL;
    }

    uint32_t fill_idx = 0;
    uint32_t reserved = xsk_ring_prod__reserve(&xsk->fill, XSK_RING_PROD__DEFAULT_NUM_DESCS, &fill_idx);
    if (reserved != XSK_RING_PROD__DEFAULT_NUM_DESCS) {
        fprintf(stderr, "[SIP_ERROR] Failed to reserve fill ring descriptors\n");
        xsk_umem__delete(xsk->umem);
        free(xsk->umem_area);
        free(xsk);
        return NULL;
    }

    for (uint32_t i = 0; i < XSK_RING_PROD__DEFAULT_NUM_DESCS; i++) {
        *xsk_ring_prod__fill_addr(&xsk->fill, fill_idx + i) = (uint64_t)(i * UMEM_FRAME_SIZE);
    }
    xsk_ring_prod__submit(&xsk->fill, XSK_RING_PROD__DEFAULT_NUM_DESCS);

    struct xsk_socket_config xsk_cfg = {
        .rx_size = XSK_RING_CONS__DEFAULT_NUM_DESCS,
        .tx_size = XSK_RING_PROD__DEFAULT_NUM_DESCS,
        .libxdp_flags = 0,
        .xdp_flags = XDP_FLAGS_SKB_MODE,
        .bind_flags = XDP_USE_NEED_WAKEUP
    };

    ret = xsk_socket__create(&xsk->xsk_sock, ifname, queue_id, xsk->umem, &xsk->rx, &xsk->tx, &xsk_cfg);
    if (ret != 0) {
        fprintf(stderr, "[SIP_ERROR] xsk_socket__create failed on %s: %d (%s)\n", ifname, ret, strerror(-ret));
        xsk_umem__delete(xsk->umem);
        free(xsk->umem_area);
        free(xsk);
        return NULL;
    }

    xsk->xsk_fd = xsk_socket__fd(xsk->xsk_sock);
    printf("[SIP_INIT] AF_XDP ring structure successfully initialized and bound on %s [Queue %u] [FD: %d]\n", 
           ifname, queue_id, xsk->xsk_fd);

    return xsk;
}
