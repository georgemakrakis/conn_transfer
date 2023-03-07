#!/bin/bash

# for i in {1..1000}
for i in {1..100}
# for i in {1..1}
do
    echo "LOOP {$i}"
    # Start Containers
    docker start load-balancer
    docker start client_1
    docker start server_1

    # (For measuring the spwan of containers we need these commented out)
    docker start server_2
    docker start server_3

    # Start Python servers and the C program for dumping sockets
    docker exec load-balancer /bin/bash /root/run_LB.sh /migvolume1/logs/LB.log

    docker exec server_1 /bin/bash /root/run_server.sh 172.20.0.3 /migvolume1/logs/server_1.log
    docker exec server_1 /bin/bash /root/run_dump.sh

    # (For measuring the spwan of containers we need these commented out)
    docker exec server_2 /bin/bash /root/run_server.sh 172.20.0.4 /migvolume1/logs/server_2.log
    docker exec server_2 /bin/bash /root/run_dump.sh

    docker exec server_3 /bin/bash /root/run_server.sh 172.20.0.5 /migvolume1/logs/server_3.log
    docker exec server_3 /bin/bash /root/run_dump.sh

    # # Capture packets at the client side and at the LB
    # docker run -d --rm --net=container:client_1 -v $PWD/tcpdump/client_1:/tcpdump --name tcpdump_1 kaazing/tcpdump
    # docker run -d --rm --net=container:load-balancer -v $PWD/tcpdump/load-balancer:/tcpdump --name tcpdump_2 kaazing/tcpdump

    # # Running the client
    docker exec client_1 /bin/bash /root/run_client.sh

    sleep 10

    # # Stopping all containers
    docker stop server_1 && docker stop server_2 && docker stop server_3 && docker stop client_1 && docker stop load-balancer
    # docker stop server_1 && docker stop client_1 && docker stop load-balancer

    # Only for container spawning
    # /bin/bash ./delete_containers.sh

    # Change the name of the PCAPs so they will not be overwritten
    # mv tcpdump/client_1/tcpdump.pcap tcpdump/client_1/tcpdump_$i.pcap
    # mv tcpdump/load-balancer/tcpdump.pcap tcpdump/load-balancer/tcpdump_$i.pcap

    docker stop tcpdump_1 && docker stop tcpdump_2

    sleep 3
done

#docker run -it --privileged --net migrate-net --ip 172.20.0.7 -d -v socket_migration_volume:/migvolume1 --name server_3 --hostname server_3 server && docker exec server_3 service ssh start && docker exec -it server_3 /bin/bash
#docker run -it --privileged --net migrate-net --ip 172.20.0.7 -d -v socket_migration_volume:/migvolume1 --name server_3 --hostname server_3 server && docker exec server_3 service ssh start && docker exec server_3 bash -c '/usr/bin/python single/echo_threading.py --ip=172.20.0.7 > single/server.log &'
