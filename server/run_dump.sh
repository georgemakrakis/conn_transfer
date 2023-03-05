#!/bin/bash

cd single && touch /migvolume1/BBB.txt && find /migvolume1/ -maxdepth 1 -type f -delete && gcc server_UNIX_sock.c -lsoccr -luuid -lnet -o server_UNIX_sock.o -I include -L lib  && ./server_UNIX_sock.o &