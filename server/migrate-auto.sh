#!/bin/bash

#sudo rm img-dir/*
rm /root/img-dir/*

criu dump --tree $1 --images-dir /root/img-dir/ -v4 -o dump.log --shell-job --tcp-established
#sudo criu dump --tree $1 --images-dir img-dir/ -v4 -o dump.log --shell-job --tcp-established --leave-stopped

#sudo scp -r img-dir/ geo@192.168.1.143:/home/geo/conn_transfer/
#sudo sshpass -p 123456 scp -r img-dir/ geo@192.168.1.143:/home/geo/conn_transfer/


sshpass -p 123456 scp -o "StrictHostKeyChecking=no" -r /root/img-dir/ root@172.20.0.4:/root

#ssh root@192.168.108.130 'criu restore --images-dir /root/CRIU_TCP_Example/img-dir -v4 -o rst.log --shell-job --tcp-established'
#sudo sshpass -p 123456 ssh -t geo@192.168.1.143 'sudo criu restore --images-dir /home/geo/conn_transfer/img-dir -v4 -o rst.log --shell-job --tcp-established'

sshpass -p 123456 ssh -t root@172.20.0.4 'criu restore --images-dir /root/img-dir -v4 -o rst.log --shell-job --tcp-established'


