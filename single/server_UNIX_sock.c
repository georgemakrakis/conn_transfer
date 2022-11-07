#include <sys/socket.h>
#include <sys/un.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <signal.h>

#define BUFFER_LENGTH 5

int main(int argc, char *argv[]){
    int listfd;
    int connfd;

    char buffer[BUFFER_LENGTH];

    /*
    * Create Sockets
    */
    listfd = socket(AF_UNIX, SOCK_STREAM, 0);
    if(listfd == -1)
        exit(-1);

    struct sockaddr_un saddr = {AF_UNIX, "/tmp/test"};
    unlink("/tmp/test");
    int receive = bind(listfd, (struct sockaddr *)&saddr, sizeof(saddr));

    receive = listen(listfd, 10);

    fflush(stdout);
    printf("Running...\n");

    /*
    * Listen for connections
    * and send random phrase on accept
    */
    while(1){
        connfd = accept(listfd, NULL, NULL);
        int length = BUFFER_LENGTH;
        receive = setsockopt(connfd, SOL_SOCKET, SO_RCVLOWAT,
                                          (char *)&length, sizeof(length));
        receive = recv(connfd, buffer, sizeof(buffer), 0);
        if (receive < 0)
        {
            printf("recv() failed");
            //break;
        }
        printf("Hit...\n");

        close(connfd);
        sleep(1);
    }

    exit(0);
}
