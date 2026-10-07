#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sqlite3.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>

#define SHM_NAME "/sip_mesh_shm"

typedef struct {
    int active_nodes;
    unsigned long processed_packets;
    unsigned long dropped_packets;
} MeshTelemetry;

int main() {
    sqlite3 *db;
    sqlite3_open("sip_mesh_state.db", &db);
    sqlite3_exec(db, "PRAGMA journal_mode=WAL;", 0, 0, 0);
    sqlite3_exec(db, "CREATE TABLE IF NOT EXISTS telemetry (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, active_nodes INT, processed INT);", 0, 0, 0);

    int shm_fd = shm_open(SHM_NAME, O_RDWR, 0666);
    if (shm_fd == -1) {
        printf("[PERSISTENCE] Shared memory not active yet.\n");
        sqlite3_close(db);
        return 1;
    }
    
    MeshTelemetry *mesh = mmap(0, sizeof(MeshTelemetry), PROT_READ, MAP_SHARED, shm_fd, 0);

    char query[256];
    snprintf(query, sizeof(query), "INSERT INTO telemetry (active_nodes, processed) VALUES (%d, %lu);", mesh->active_nodes, mesh->processed_packets);
    sqlite3_exec(db, query, 0, 0, 0);

    printf("[PERSISTENCE] Logged -> Active Nodes: %d | Processed: %lu\n", mesh->active_nodes, mesh->processed_packets);
    sqlite3_close(db);
    return 0;
}
