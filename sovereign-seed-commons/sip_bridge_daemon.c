#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <time.h>
#include <sqlite3.h>
#include <x86intrin.h>
#include "sip_commons_bridge.h"

static volatile int keep_running = 1;

void handle_sigint(int sig) {
    keep_running = 0;
}

int main() {
    int shm_fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if (shm_fd == -1) {
        perror("shm_open");
        exit(EXIT_FAILURE);
    }
    
    if (ftruncate(shm_fd, sizeof(sip_shm_ring_t)) == -1) {
        perror("ftruncate");
        exit(EXIT_FAILURE);
    }

    sip_shm_ring_t *ring = mmap(NULL, sizeof(sip_shm_ring_t), PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (ring == MAP_FAILED) {
        perror("mmap");
        exit(EXIT_FAILURE);
    }

    sqlite3 *db;
    char *err_msg = 0;
    int rc = sqlite3_open("sip_ledger.db", &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        exit(EXIT_FAILURE);
    }

    sqlite3_exec(db, "PRAGMA journal_mode=WAL;", 0, 0, &err_msg);
    sqlite3_exec(db, "PRAGMA synchronous=NORMAL;", 0, 0, &err_msg);
    sqlite3_exec(db, "CREATE TABLE IF NOT EXISTS commons_events (trace_id INTEGER PRIMARY KEY, timestamp INTEGER, payload TEXT);", 0, 0, &err_msg);

    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db, "INSERT INTO commons_events (trace_id, timestamp, payload) VALUES (?, ?, ?);", -1, &stmt, 0);

    uint64_t local_tail = atomic_load(&ring->tail);
    printf("[SIP_BRIDGE] Attached to shared memory ring. Polling active.\n");

    while (keep_running) {
        uint64_t local_head = atomic_load_explicit(&ring->head, memory_order_acquire);
        
        if (local_tail == local_head) {
            _mm_pause();
            continue;
        }

        sip_event_t *ev = &ring->events[local_tail & RING_MASK];

        sqlite3_bind_int64(stmt, 1, ev->trace_id);
        sqlite3_bind_int64(stmt, 2, ev->timestamp_ns);
        sqlite3_bind_text(stmt, 3, (char *)ev->data, ev->payload_len, SQLITE_STATIC);
        
        sqlite3_exec(db, "BEGIN TRANSACTION;", 0, 0, 0);
        sqlite3_step(stmt);
        sqlite3_exec(db, "COMMIT;", 0, 0, 0);
        sqlite3_reset(stmt);

        local_tail++;
        atomic_store_explicit(&ring->tail, local_tail, memory_order_release);
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);
    munmap(ring, sizeof(sip_shm_ring_t));
    printf("[SIP_BRIDGE] Clean shutdown executed.\n");
    return 0;
}
