#!/bin/bash

route del default gw 172.20.0.1
route add default gw 172.20.0.2
route del -net 172.20.0.0 gw 0.0.0.0 netmask 255.255.0.0 dev eth0