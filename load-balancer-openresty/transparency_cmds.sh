#!/bin/bash

ip rule add fwmark 1 lookup 100
ip route add local 0.0.0.0/0 dev lo table 100
iptables -t mangle -A PREROUTING -p tcp -s 172.20.0.0/16 --sport 80 -j MARK --set-xmark 0x1/0xffffffff
