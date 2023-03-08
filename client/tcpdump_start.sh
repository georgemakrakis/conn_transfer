#!/bin/sh
rm -f nohup.out
nohup /usr/sbin/tcpdump -i any -w /root/tcpdump/client_1.pcap &

# Write tcpdump's PID to a file
echo $! > /var/run/tcpdump.pid