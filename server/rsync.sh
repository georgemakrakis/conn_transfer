#!/bin/bash

sshpass -p 123456 rsync -e "ssh -o StrictHostKeyChecking=no" -r /root/single/dumped_connections root@$1:/root/single