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
#include <unistd.h>

#include "./soccr/soccr.h"

#define handle_error(msg) do { perror(msg); exit(EXIT_FAILURE); } while(0)
#define pr_perror(fmt, ...) printf(fmt ": %m\n", ##__VA_ARGS__)

#define BUFFER_LENGTH 11

static void pr_printf(unsigned int level, const char *fmt, ...)
{
	va_list args;

	va_start(args, fmt);
	vprintf(fmt, args);
	va_end(args);
}

static void send_fd(int socket, int *fds, int n)
{
        struct msghdr msg = {0};
        struct cmsghdr *cmsg;
        char buf[CMSG_SPACE(n * sizeof(int))], dup[256];
        memset(buf, '\0', sizeof(buf));
        struct iovec io = { .iov_base = &dup, .iov_len = sizeof(dup) };

        msg.msg_iov = &io;
        msg.msg_iovlen = 1;
        msg.msg_control = buf;
        msg.msg_controllen = sizeof(buf);

        cmsg = CMSG_FIRSTHDR(&msg);
        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = CMSG_LEN(n * sizeof(int));

        memcpy ((int *) CMSG_DATA(cmsg), fds, n * sizeof (int));

        if (sendmsg (socket, &msg, 0) < 0)
                handle_error ("Failed to send message");
}

int main()
{	
	//union libsoccr_addr client_addr, my_addr;
	struct libsoccr_sk *so, *so_rst;
	struct libsoccr_sk_data data = {};
	struct libsoccr_sk_data rst_data = {};

	char buffer[BUFFER_LENGTH] = "0123456789", *queue;

	libsoccr_set_log(10, pr_printf);

	FILE *file;

	file = fopen ("dump.dat", "r");
	if (file == NULL)
	{
		fprintf(stderr, "\nError opening file\n");
		exit (1);
	}

	while(fread(&rst_data, sizeof(rst_data), 1, file))
		printf ("Reading %ld data...\n", sizeof(rst_data));

	fclose (file);

	file = fopen ("dump.dat", "r");
	if (file == NULL)
	{
		fprintf(stderr, "\nError opening file\n");
		exit (1);
	}

	while(fread(&rst_data, sizeof(rst_data), 1, file))
		printf ("Reading %ld data...\n", sizeof(rst_data));

	fclose (file);

	char buffer2 [100], *inq;
	char buffer3 [100], *outq;

	file = fopen ("dump_inq.dat", "r");
	if (file == NULL)
	{
		fprintf(stderr, "\nError opening file\n");
		exit (1);
	}

	while(fread(&inq, sizeof(inq), 1, file))
		printf ("Reading %ld data...\n", sizeof(inq));

	fclose (file);

	file = fopen ("dump_inq.dat", "r");
	if (file == NULL)
	{
		fprintf(stderr, "\nError opening file\n");
		exit (1);
	}

	while(fread(&outq, sizeof(outq), 1, file))
		printf ("Reading %ld data...\n", sizeof(outq));

	fclose (file);

	// Restore
	int rst = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	if (rst == -1){
		perror("Restore socket creation");
		printf("Here fail\n");
		return -1;
	}
	
	//so_rst = malloc(sizeof(struct libsoccr_sk *));
	so_rst = libsoccr_pause(rst);
	printf("Here\n");

	//libsoccr_set_addr(so_rst, 1, &my_addr, 0);
	//libsoccr_set_addr(so_rst, 0, &client_addr, 0);
	
	//char s[INET6_ADDRSTRLEN > INET_ADDRSTRLEN ? INET6_ADDRSTRLEN : INET_ADDRSTRLEN] = "\0";
	//inet_ntop(AF_INET, &(my_addr.v4.sin_addr), s, INET_ADDRSTRLEN);
	//printf("IP address: %s\n", s);
	
	//inet_ntop(AF_INET, &(client_addr.v4.sin_addr), s, INET_ADDRSTRLEN);
	//printf("IP address client: %s\n", s);
	
	//struct sockaddr_in client_addr;
	union libsoccr_addr client_addr;
	client_addr.v4.sin_family = AF_INET;
	//client_addr.v4.sin_addr.s_addr = inet_addr("192.168.1.1");
	// client_addr.v4.sin_addr.s_addr = inet_addr("192.168.1.142");
	client_addr.v4.sin_addr.s_addr = inet_addr("172.20.0.2");
	// TODO: This is changed manually
	client_addr.v4.sin_port = htons(50630);

	//struct sockaddr_in localaddr;
	union libsoccr_addr localaddr;
	localaddr.v4.sin_family = AF_INET;
	// localaddr.v4.sin_addr.s_addr = inet_addr("192.168.1.143");
	localaddr.v4.sin_addr.s_addr = inet_addr("172.20.0.4");
	localaddr.v4.sin_port = htons(80);

	libsoccr_set_addr(so_rst, 1, &localaddr, 0);
	libsoccr_set_addr(so_rst, 0, &client_addr, 0);

	libsoccr_set_queue_bytes(so_rst, TCP_SEND_QUEUE, outq, SOCCR_MEM_EXCL);
	libsoccr_set_queue_bytes(so_rst, TCP_RECV_QUEUE, inq, SOCCR_MEM_EXCL);

	int ret = libsoccr_restore(so_rst, &rst_data, sizeof(rst_data));
	if (ret){
		//perror("Restore fail");
		pr_perror("libsoccr_restore: %d", ret);
		printf("Code: %d \n", ret);
		//return 1;
	}

	queue = libsoccr_get_queue_bytes(so_rst, TCP_RECV_QUEUE, SOCCR_MEM_EXCL);
	printf("Data RECV after: %s \n", queue);

	queue = libsoccr_get_queue_bytes(so_rst, TCP_SEND_QUEUE, SOCCR_MEM_EXCL);
	printf("Data SEND after: %s \n", queue);


	int listfd = socket(AF_UNIX, SOCK_STREAM, 0);
	if(listfd == -1)
		exit(-1);


	// Let's take the data, RECV_Q and SEND_Q from the migrated socket and port them to the current one using the transferred files

	struct sockaddr_un saddr = {AF_UNIX, "/tmp/test"};
	//unlink("/tmp/test");
	if (connect(listfd, (struct sockaddr *) &saddr, sizeof(struct sockaddr_un)) == -1)
                handle_error ("Failed to connect to socket");


	send_fd(listfd, &(so_rst->fd), 1);
	printf("Sent FD \n");

	//sleep(20);
	
	libsoccr_resume(so_rst);
	printf("Resumed\n");
	printf("Sock Descr: %d\n", so_rst->fd);
}