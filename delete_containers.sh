#!/bin/bash

# for i in {2..50}
for i in {2..25}
do
   docker stop "server_$i" && docker rm "server_$i"
done