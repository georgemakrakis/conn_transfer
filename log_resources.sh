#!/bin/bash

# changed to set the PID but otherwise used from: 

# PNAME="$1"
PID="$1"
LOG_FILE="$2"

while true ; do
    echo "$(date) :: $(ps -p ${PID} -o %cpu,%mem | tail -1)%" >> $LOG_FILE
    # echo "$(date) :: $PNAME[$(pidof ${PNAME})] $(ps -C ${PNAME} -o %cpu | tail -1)%" >> $LOG_FILE
    # sleep 2
    sleep 0.1
done
