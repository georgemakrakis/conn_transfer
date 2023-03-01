#!/bin/bash

#docker run -it --privileged --net migrate-net --ip 172.20.0.7 -d -v socket_migration_volume:/migvolume1 --name server_3 --hostname server_3 server && docker exec server_3 service ssh start && docker exec -it server_3 /bin/bash
docker run -it --privileged --net migrate-net --ip 172.20.0.7 -d -v socket_migration_volume:/migvolume1 --name server_3 --hostname server_3 server && docker exec server_3 service ssh start && docker exec server_3 bash -c '/usr/bin/python single/echo_threading.py --ip=172.20.0.7 > single/server.log &'
