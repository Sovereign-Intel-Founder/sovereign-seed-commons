#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>
#include <dirent.h>

#define PORT 9999
#define SHM_NAME "/sip_mesh_shm"

typedef struct {
    int active_nodes;
    unsigned long processed_packets;
    unsigned long dropped_packets;
} MeshTelemetry;

int scan_local_nodes() {
    int count = 1;
    DIR *d = opendir(".");
    struct dirent *dir;
    if (d) {
        while ((dir = readdir(d)) != NULL) {
            if (strstr(dir->d_name, "cell_node") != NULL || 
                strstr(dir->d_name, "tollbridge") != NULL ||
                strstr(dir->d_name, "evidence") != NULL) {
                count++;
            }
        }
        closedir(d);
    }
    return count;
}

int main() {
    printf("SOVEREIGN INTELLIGENCE PROTOCOL - MULTI-CLONE MESH CORE\n");

    int shm_fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    ftruncate(shm_fd, sizeof(MeshTelemetry));
    MeshTelemetry *mesh = mmap(0, sizeof(MeshTelemetry), PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    
    mesh->processed_packets = 0;
    mesh->dropped_packets = 0;

    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in servaddr = {0}, cliaddr;
    servaddr.sin_family = AF_INET;
    servaddr.sin_addr.s_addr = INADDR_ANY;
    servaddr.sin_port = htons(PORT);

    bind(sockfd, (struct sockaddr *)&servaddr, sizeof(servaddr));

    struct timeval tv = {1, 0};
    setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    int remote_clones = 0;
    char buffer[512];
    while(1) {
        socklen_t len = sizeof(cliaddr);
        if (recvfrom(sockfd, buffer, sizeof(buffer)-1, 0, (struct sockaddr *)&cliaddr, &len) > 0) {
            mesh->processed_packets++;
            remote_clones++; // Register connecting clone/duplicate
        }

        mesh->active_nodes = scan_local_nodes() + remote_clones;

        printf("[MESH SYNC] Local & Clone Nodes Active: %d | Total Packets: %lu\n", 
               mesh->active_nodes, mesh->processed_packets);
        fflush(stdout);
        sleep(2);
    }
    return 0;
}
