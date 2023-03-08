#include <sys/socket.h>
#include <arpa/inet.h>
#include <sys/un.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <signal.h>
#include <stdarg.h>
#include <uuid/uuid.h>

#include "./soccr/soccr.h"

#define BUFFER_LENGTH 5

#define handle_error(msg) do { perror(msg); exit(EXIT_FAILURE); } while(0)
#define pr_perror(fmt, ...) printf(fmt ": %m\n", ##__VA_ARGS__)

static void pr_printf(unsigned int level, const char *fmt, ...)
{
	va_list args;

	va_start(args, fmt);
	vprintf(fmt, args);
	va_end(args);
}

// Adpopted from: https://stackoverflow.com/a/51068240
char *produce_uuid()
{
	uuid_t binuuid;
    /*
     * Generate a UUID. We're not done yet, though,
     * for the UUID generated is in binary format 
     * (hence the variable name). We must 'unparse' 
     * binuuid to get a usable 36-character string.
     */

    // uuid_generate_random(binuuid);

    uuid_generate(binuuid);

    /*
     * uuid_unparse() doesn't allocate memory for itself, so do that with
     * malloc(). 37 is the length of a UUID (36 characters), plus '\0'.
     */
    char *uuid = malloc(37);

    /*
     * Produces a UUID string at uuid consisting of letters
     * whose case depends on the system's locale.
     */
    uuid_unparse(binuuid, uuid);

    return uuid;
}

// Adopted From: https://stackoverflow.com/a/2358843/7189378
ssize_t read_fd(int fd, void *ptr, size_t nbytes, int *recvfd)
{
    struct msghdr   msg;
    struct iovec    iov[1];
    ssize_t         n;
    int             newfd;

    union {
      struct cmsghdr    cm;
      char              control[CMSG_SPACE(sizeof(int))];
    } control_un;
    struct cmsghdr  *cmptr;

    msg.msg_control = control_un.control;
    msg.msg_controllen = sizeof(control_un.control);

    msg.msg_name = NULL;
    msg.msg_namelen = 0;

    iov[0].iov_base = ptr;
    iov[0].iov_len = nbytes;
    msg.msg_iov = iov;
    msg.msg_iovlen = 1;

    if ( (n = recvmsg(fd, &msg, 0)) <= 0)
        return(n);

    if ( (cmptr = CMSG_FIRSTHDR(&msg)) != NULL &&
        cmptr->cmsg_len == CMSG_LEN(sizeof(int))) {
        if (cmptr->cmsg_level != SOL_SOCKET)
            //err_quit("control level != SOL_SOCKET");
            printf("control level != SOL_SOCKET");
        if (cmptr->cmsg_type != SCM_RIGHTS)
            //err_quit("control type != SCM_RIGHTS");	
            printf("control type != SCM_RIGHTS");
        *recvfd = *((int *) CMSG_DATA(cmptr));
    } else
        *recvfd = -1;       /* descriptor was not passed */

    return(n);
}
/* end read_fd */

static
int * recv_fd(int socket, int n) {
//int recv_fd(int socket, int n) {
        int *fds = malloc (n * sizeof(int));
        //int fds;
        struct msghdr msg = {0};
        struct cmsghdr *cmsg;
        char buf[CMSG_SPACE(n * sizeof(int))], dup[256];
        memset(buf, '\0', sizeof(buf));
        struct iovec io = { .iov_base = &dup, .iov_len = sizeof(dup) };

        msg.msg_iov = &io;
        msg.msg_iovlen = 1;
        msg.msg_control = buf;
        msg.msg_controllen = sizeof(buf);

        if (recvmsg (socket, &msg, 0) < 0)
                handle_error ("Failed to receive message");

        cmsg = CMSG_FIRSTHDR(&msg);

        memcpy (fds, (int *) CMSG_DATA(cmsg), n * sizeof(int));
        //fds = *((int *) CMSG_DATA(cmsg));

        return fds;
}

char *concat_file_name(char *new_uuid, char *path, char *file_name)
{
	size_t n = strlen(new_uuid) + strlen(path) + strlen(file_name) + 1 + 1;
	char *final_file_name = malloc(n);

	strncpy(final_file_name, path, n);			
	strcat(final_file_name, new_uuid);
	strcat(final_file_name, "_");
	strcat(final_file_name, file_name);

	return final_file_name;
}

int main(int argc, char *argv[])
{
    int listfd;
    int connfd;
    struct libsoccr_sk *so, *so_rst;
    struct libsoccr_sk_data data = {};
    struct libsoccr_sk_data rst_data = {};

	// int thread_num = 1;

    char buffer[BUFFER_LENGTH], *queue;

    libsoccr_set_log(10, pr_printf);

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
    */
    while(1)
    {
        connfd = accept(listfd, NULL, NULL);
        int length = BUFFER_LENGTH;
        receive = setsockopt(connfd, SOL_SOCKET, SO_RCVLOWAT,
                                          (char *)&length, sizeof(length));
        //receive = recv(connfd, buffer, sizeof(buffer), 0);
        //if (receive < 0)
        //{
        //    printf("recv() failed");
        //    //break;
        //}
        printf("Hit...\n");
        char c;
        int *fd_rec;
        //int fd_rec;

        //read_fd(connfd, &c, 5, &fd_rec);
        fd_rec = recv_fd(connfd, 1);
        //printf("FD: %d \n", fd_rec);
		



	    ssize_t nbytes;
        for (int i=0; i<2; ++i) {
                fprintf (stdout, "Sock fd %d\n", fd_rec[i]);
                //while ((nbytes = read(fd_rec[i], buffer, sizeof(buffer))) > 0)
                //        write(1, buffer, nbytes);
                //*buffer = '\0';
                // TODO: Need to change this one to include which particular socket we want
		if (fd_rec[i] > 0) {
			union libsoccr_addr client_addr, my_addr;
			// Finding addresses before we pause
			socklen_t addr_size = sizeof(my_addr);
			getsockname(fd_rec[i], (struct sockaddr *)&my_addr, &addr_size);
			
			addr_size = sizeof(client_addr);
			getpeername(fd_rec[i], (struct sockaddr *) &client_addr, &addr_size);
			
			client_addr.v4.sin_family = AF_INET;
			my_addr.v4.sin_family = AF_INET;

			so = libsoccr_pause(fd_rec[i]);	     
			printf("Paused\n");
		       
			int dsize = libsoccr_save(so, &data, sizeof(data));
			//printf("dumped size %ld \n", sizeof(data));
			if (dsize < 0) {
				perror("libsoccr_save");
				return -1;
			}

			// The UUID is mostly meant to make the process more automated for many sockets
			// char *new_uuid = produce_uuid();
			// char *new_uuid = "";
			char *new_uuid = malloc(200);
			// int thread_num = fd_rec[i] - 4;
			int thread_num = fd_rec[i];
			snprintf(new_uuid, 200, "%d", thread_num);
			// printf("NEW UUID PRODUCED %s\n", new_uuid);

			// TODO: save all the above to a file and read from it to restore the socket
			FILE *file;

			char *path = "/migvolume1/";
			// char *path = "/root/single/dumped_connections/";
			char *file_name = "dump.dat";

			char *final_file_name = concat_file_name(new_uuid, path, file_name);
			
			
			printf("Dumping %d with file name %s\n", fd_rec[i], final_file_name);

			file = fopen (final_file_name, "w");
			if (file == NULL)
			{
				fprintf(stderr, "Error opening file\n");
				exit (1);
			}
	
			fwrite (&data, sizeof(data), 1, file);	     
			if(fwrite != 0)
				printf("contents to file written successfully !\n");
			else
				printf("error writing file !\n");
		 
		 	fclose (file);

            // Write the RECV and SEND queues to files
            char buffer2 [100], *inq;
            char buffer3 [100], *outq;
            inq = libsoccr_get_queue_bytes(so, TCP_RECV_QUEUE, 0);
            outq = libsoccr_get_queue_bytes(so, TCP_SEND_QUEUE, 0);

			file_name = "dump_inq.dat";

			final_file_name = concat_file_name(new_uuid, path, file_name);

            file = fopen (final_file_name, "w");
			if (file == NULL)
			{
				fprintf(stderr, "Error opening file\n");
				exit (1);
			}
	
			fwrite (&inq, sizeof(inq), 1, file);	     
			if(fwrite != 0)
				printf("contents to file inq written successfully !\n");
			else
				printf("error writing file !\n");
		 
		 	fclose (file);

			file_name = "dump_outq.dat";

			final_file_name = concat_file_name(new_uuid, path, file_name);

            file = fopen (final_file_name, "w");
			if (file == NULL)
			{
				fprintf(stderr, "Error opening file\n");
				exit (1);
			}
	
			fwrite (&outq, sizeof(outq), 1, file);	     
			if(fwrite != 0)
				printf("contents to file outq written successfully !\n");
			else
				printf("error writing file !\n");
		 
		 	fclose (file);

			printf("Resuming...\n");
			libsoccr_resume(so);

			printf("Closing %d...\n", fd_rec[i]);
			close(fd_rec[i]);

			// thread_num++;

			//close(fd_rec[i]);			

			// sleep(5);

			// file = fopen ("dump.dat", "r");
			// if (file == NULL)
			// {
			// 	fprintf(stderr, "Error opening file\n");
			// 	exit (1);
			// }
			
			// while(fread(&rst_data, sizeof(rst_data), 1, file))
			// 	printf ("Reading %ld data...\n", sizeof(rst_data));

			// fclose (file);

            // int client_close_stat = close(fd_rec[i]);
            // printf("Closed client socket as well... with %d\n", client_close_stat);

			// // Restore
			// int rst = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
			// if (rst == -1){
			// 	perror("Restore socket creation");
			// 	printf("Here fail\n");
			// 	return -1;
			// }
			// printf("Here\n");


			// so_rst = libsoccr_pause(rst);

			// These are like that because we are dumping the client before.
			//libsoccr_set_addr(so_rst, 1, &my_addr, 0);
			//libsoccr_set_addr(so_rst, 0, &client_addr, 0);
			
			//libsoccr_set_addr(so_rst, 1, &client_addr, 0);
			//libsoccr_set_addr(so_rst, 0, &my_addr, 0);

			//queue = libsoccr_get_queue_bytes(so, TCP_RECV_QUEUE, SOCCR_MEM_EXCL);
			//libsoccr_set_queue_bytes(so_rst, TCP_RECV_QUEUE, queue, SOCCR_MEM_EXCL);
			//queue = libsoccr_get_queue_bytes(so, TCP_SEND_QUEUE, SOCCR_MEM_EXCL);
			//libsoccr_set_queue_bytes(so_rst, TCP_SEND_QUEUE, queue, SOCCR_MEM_EXCL);

			//int ret = libsoccr_restore(so_rst, &data, dsize);
			//if (ret)
			//	perror("Restore fail");
			//	return -1;
			//printf("Restored\n");

			//libsoccr_resume(so_rst);

			// ===============
			// libsoccr_set_addr(so_rst, 1, &my_addr, 0);
			// libsoccr_set_addr(so_rst, 0, &client_addr, 0);
			
			// char s[INET6_ADDRSTRLEN > INET_ADDRSTRLEN ? INET6_ADDRSTRLEN : INET_ADDRSTRLEN] = "\0";
			// inet_ntop(AF_INET, &(my_addr.v4.sin_addr), s, INET_ADDRSTRLEN);
			// printf("IP address: %s\n", s);
			
			// inet_ntop(AF_INET, &(client_addr.v4.sin_addr), s, INET_ADDRSTRLEN);
			// printf("IP address client: %s\n", s);

			// libsoccr_set_addr(so, 1, &client_addr, 0);
			// libsoccr_set_addr(so, 0, &my_addr, 0);

			// int ret = libsoccr_restore(so, &rst_data, sizeof(rst_data));
			// if (ret){
			// 	//perror("Restore fail");
			// 	pr_perror("libsoccr_restore: %d", ret);
			// 	printf("Code: %d \n", ret);
			// 	//return 1;
			// }
			
			//libsoccr_resume(so);
			//printf("Resumed\n");
		}
	    }

        // close(connfd);
		// printf("Closed UDS\n");
		
        // sleep(1);
    }

    exit(0);
}
