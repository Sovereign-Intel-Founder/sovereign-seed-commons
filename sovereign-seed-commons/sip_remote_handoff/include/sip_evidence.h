#ifndef SIP_EVIDENCE_H
#define SIP_EVIDENCE_H

#include <stdint.h>
#include <stddef.h>

// Structure mapping to V-SLOA-VERTICAL-001 / REQ-015 evidence requirements
typedef struct {
    const char *framework;
    const char *evidence_class;
    const char *registry_id;
    const char *interface_name;
    uint32_t queue_id;
    uint64_t total_packets;
    uint64_t total_bytes;
    int execution_status;
} sip_evidence_record_t;

int sip_write_evidence_object(const sip_evidence_record_t *record, const char *filepath);

#endif // SIP_EVIDENCE_H
