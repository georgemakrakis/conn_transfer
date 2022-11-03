#!/bin/bash

for ((i=1;i<=3;i++)); do
   curl -v --header "Connection: keep-alive" "http://172.20.0.2/counter"; =
done