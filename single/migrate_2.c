#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <net/if.h>
#include <arpa/inet.h>

#include "./soccr/soccr.h"


#define BUFFER_SIZE 1024
#define on_error(...) { fprintf(stderr, __VA_ARGS__); fflush(stderr); exit(1); }

int main(int argc, char *argv[])
{
    if (argc < 3) on_error("Usage: %s [client IP] [client port]\n", argv[0]);

    struct sockaddr_in client_address;

    char str[INET_ADDRSTRLEN];

    // store this IP address in sa:
    inet_pton(AF_INET, argv[1], &(client_address.sin_addr));

    int port = atoi(argv[2]);
    
    socklen_t client_len = sizeof(client_address);
    int client_fd, rst, err;

    if (getsockname(client_fd, (struct sockaddr *) &client_address, &client_len)) 
    {
        //pr_perror("connect");
        perror("connect 1");
        return -1;
    }

    //dst_let = sizeof(client);
    if (getpeername(client_fd, (struct sockaddr *) &client_address, &client_len)) 
    {
        //pr_perror("connect");
        perror("connect 2");
        return -1;
    }

    //printf("Paused\n");
    //so = libsoccr_pause(client_fd);

    //int dsize = libsoccr_save(so, &data, sizeof(data));
    //if (dsize < 0) {
    //    perror("libsoccr_save");
    //    return -1;
    //}
    //printf("Saved\n");

    //close(client_fd);

    return 0;
}
