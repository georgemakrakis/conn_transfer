#!/bin/bash

PID="$(docker exec load-balancer ps -aux | grep 'python_load_balancer_threading' | awk '{print $2}')"
docker exec load-balancer kill -9 $PID