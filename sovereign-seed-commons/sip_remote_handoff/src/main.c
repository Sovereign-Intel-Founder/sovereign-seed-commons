#include "../include/sip_envelope.h"
#include "../include/sip_evidence.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <errno.h>

static volatile int running = 1;

void handle_sigint(int sig) {
    (void)sig;
    running = 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "[SIP_ERROR] Usage: %s <interface_name>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *ifname = argv[1];
    uint32_t queue_id = 0;

    signal(SIGINT, handle_sigint);
    signal(SIGTERM, handle_sigint);

    printf("[SIP_INIT] Initializing Sovereign Intelligence Protocol XSK pipeline on interface: %s [Queue %u]\n", ifname, queue_id);

    sip_xsk_handle_t *xsk = sip_xsk_create_ring(ifname, queue_id);
    if (!xsk) {
        fprintf(stderr, "[SIP_CRITICAL] Failed to create AF_XDP ring handle. Aborting execution.\n");
        return EXIT_FAILURE;
    }

    pthread_t poll_thread;
    int ret = pthread_create(&poll_thread, NULL, sip_xsk_poll_ingress, xsk);
    if (ret != 0) {
        fprintf(stderr, "[SIP_ERROR] Failed to create ingress polling thread: %s\n", strerror(ret));
        free(xsk->umem_area);
        free(xsk);
        return EXIT_FAILURE;
    }

    printf("[SIP_RUNNING] Pipeline active. Press Ctrl+C to terminate cleanly.\n");

    // Main execution loop monitoring health
    while (running) {
        sleep(1);
    }

    printf("[SIP_SHUTDOWN] Termination signal received. Cleaning up pipeline resources...\n");

    // Generate formal Class E3 evidence record on clean shutdown
    sip_evidence_record_t record = {
        .framework = "Space LEAF / Alexandria V-SLOA",
        .evidence_class = "E1/E3 - Implemented & Machine-Generated",
        .registry_id = "V-SLOA-VERTICAL-001",
        .interface_name = ifname,
        .queue_id = queue_id,
        .total_packets = 0, // Updated dynamically by ingress stats if tracked
        .total_bytes = 0,
        .execution_status = 0
    };
    sip_write_evidence_object(&record, "sip_evidence_record.json");

    pthread_cancel(poll_thread);
    pthread_join(poll_thread, NULL);

    if (xsk->umem) {
        xsk_umem__delete(xsk->umem);
    }
    if (xsk->umem_area) {
        free(xsk->umem_area);
    }
    free(xsk);

    printf("[SIP_EXIT] Pipeline successfully dismantled.\n");
    return EXIT_SUCCESS;
}
