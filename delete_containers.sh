#!/bin/bash

MAX=$1

# for i in {2..10}
for i in $(seq 2 $MAX)
do
   docker stop "server_$i" && docker rm "server_$i"
done