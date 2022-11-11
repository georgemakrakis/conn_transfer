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

#include "./soccr/soccr.h"

#define handle_error(msg) do { perror(msg); exit(EXIT_FAILURE); } while(0)
#define pr_perror(fmt, ...) printf(fmt ": %m\n", ##__VA_ARGS__)

#define BUFFER_LENGTH 5

static void pr_printf(unsigned int level, const char *fmt, ...)
{
	va_list args;

	va_start(args, fmt);
	vprintf(fmt, args);
	va_end(args);
}

int main()
{	
	//union libsoccr_addr client_addr, my_addr;
	struct libsoccr_sk *so, *so_rst;
	struct libsoccr_sk_data data = {};
	struct libsoccr_sk_data rst_data = {};

	char buffer[BUFFER_LENGTH], *queue;

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

	// Restore
	int rst = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	if (rst == -1){
		perror("Restore socket creation");
		printf("Here fail\n");
		return -1;
	}

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
	client_addr.v4.sin_addr.s_addr = inet_addr("192.168.1.1");
	// TODO: This is changed manually
	client_addr.v4.sin_port = htons(2416);

	//struct sockaddr_in localaddr;
	union libsoccr_addr localaddr;
	localaddr.v4.sin_family = AF_INET;
	localaddr.v4.sin_addr.s_addr = inet_addr("192.168.1.143");
	localaddr.v4.sin_port = htons(80);

	libsoccr_set_addr(so_rst, 1, &localaddr, 0);
	libsoccr_set_addr(so_rst, 0, &client_addr, 0);

	int ret = libsoccr_restore(so_rst, &rst_data, sizeof(rst_data));
	if (ret){
		//perror("Restore fail");
		pr_perror("libsoccr_restore: %d", ret);
		printf("Code: %d \n", ret);
		//return 1;
	}
	
	libsoccr_resume(so_rst);
	printf("Resumed\n");
}