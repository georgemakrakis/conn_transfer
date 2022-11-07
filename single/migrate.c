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
    if (argc < 2) on_error("Usage: %s [port]\n", argv[0]);

    int port = atoi(argv[1]);

    // Change these to better names
    int sock, client_fd, rst, err;

    // Where to save the data when dumping the connection
    struct libsoccr_sk_data data = {};
    struct libsoccr_sk *so, *so_rst;

    char buf2[11] = "0123456789", *queue;

    struct sockaddr_in server, client;
    char buf[BUFFER_SIZE];
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) on_error("Could not create socket\n");

    server.sin_family = AF_INET;
    server.sin_port = htons(port);
    server.sin_addr.s_addr = htonl(INADDR_ANY);

    int opt_val = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &opt_val, sizeof opt_val);

    err = bind(sock, (struct sockaddr *) &server, sizeof(server));
    if (err < 0) on_error("Could not bind socket\n");

    err = listen(sock, 128);
    if (err < 0) on_error("Could not listen on socket\n");

    printf("Server is listening on %d\n", port);

    while (1) {
        socklen_t client_len = sizeof(client);
        client_fd = accept(sock, (struct sockaddr *) &client, &client_len);

        if (client_fd < 0) on_error("Could not establish new connection\n");
	printf("Client FD : %d", client_fd);

        while (1) {
            int read = recv(client_fd, buf, BUFFER_SIZE, 0);
            printf("Server Read\n");

            if (!read) break; // done reading
            if (read < 0) on_error("Client read failed\n");
            err = send(client_fd, buf, read, 0);
            printf("Sent\n");

            if (err < 0) on_error("Client write failed\n");
        
            /* Dump a tcp socket */
            //bzero(&addr, sizeof(addr));
            //sock=socket(PF_INET, SOCK_STREAM, 0);

            //socklen_t dst_let = sizeof(server);
            //if (getsockname(sock, (struct sockaddr *) &server, &dst_let)) {
            if (getsockname(client_fd, (struct sockaddr *) &client, &client_len)) {
                //pr_perror("connect");
                perror("connect 1");
                return -1;
            }

            //dst_let = sizeof(client);
            if (getpeername(client_fd, (struct sockaddr *) &client, &client_len)) {
            //if (getpeername(sock, (struct sockaddr *) &server, &dst_let)) {
                //pr_perror("connect");
                perror("connect 2");
                return -1;
            }

            //so = libsoccr_pause(sock);
            printf("Paused\n");
            so = libsoccr_pause(client_fd);

            int dsize = libsoccr_save(so, &data, sizeof(data));
            if (dsize < 0) {
                perror("libsoccr_save");
                return -1;
            }
            printf("Saved\n");

            close(client_fd);

            /* Restore a tcp socket */
            rst = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
            if (rst == -1)
                return -1;


            so_rst = libsoccr_pause(rst);
            libsoccr_set_addr(so_rst, 1, (union libsoccr_addr *) &server, 0);
            libsoccr_set_addr(so_rst, 0, (union libsoccr_addr *) &client, 0);

            queue = libsoccr_get_queue_bytes(so, TCP_RECV_QUEUE, SOCCR_MEM_EXCL);
            libsoccr_set_queue_bytes(so_rst, TCP_RECV_QUEUE, queue, SOCCR_MEM_EXCL);
            queue = libsoccr_get_queue_bytes(so, TCP_SEND_QUEUE, SOCCR_MEM_EXCL);
            libsoccr_set_queue_bytes(so_rst, TCP_SEND_QUEUE, queue, SOCCR_MEM_EXCL);

            int ret = libsoccr_restore(so_rst, &data, dsize);
            if (ret)
                return -1;

            libsoccr_resume(so_rst);
            libsoccr_resume(so);
            printf("Migrated\n");


        }
    }

    return 0;
}
