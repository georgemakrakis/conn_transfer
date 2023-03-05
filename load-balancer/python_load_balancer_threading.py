# From: https://gist.github.com/zhouchangxun/5750b4636cc070ac01385d89946e0a7b

import sys, logging, re, subprocess, os, argparse
import socket
import select
import random, uuid
from itertools import cycle
import threading, multiprocessing

import struct, array, time

# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done
SERVER_POOL = [('172.20.0.3', 80)]
# SERVER_POOL = [('172.20.0.3', 80), ('172.20.0.4',80)]
# SERVER_POOL = [('172.20.0.3', 80), ('172.20.0.4',80), ('172.20.0.7', 80)]

# MIG_SERVER_POOL = [('172.20.0.4', 80), ('172.20.0.3', 80)]
MIG_SERVER_POOL = [('172.20.0.4', 80), ('172.20.0.5',80)]

# These ports will be used to also identify messages that are meant for migration
#  and not client forwarded data
MIG_PORTS = []

# dumb python socket echo server, long tcp connection
# $ ~  while  python server.py
# SERVER_POOL = [('localhost', 6666)]

# TODO: See if we can reuse the above array of tuples
# IPs = ["172.20.0.3", "172.20.0.4"]

# IPs = ["172.20.0.4", "172.20.0.3"]
IPs = ["172.20.0.4", "172.20.0.3", "172.20.0.7"]

# Should that be a list inside the class?
# client_socket = None

logging.basicConfig(filename='LB_server.log', filemode='w', level=logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)

# How many containers have been spawned eventually. We start from one, and the should be an even number.
SPAWNED_CONTAINERS = 1

ITER = cycle(SERVER_POOL)
MIG_ITER = cycle(MIG_SERVER_POOL) # This one is slided one step to the right as above

logs_path = ""

def round_robin(iter):
    # round_robin([A, B, C, D]) --> A B C D A B C D A B C D ...
    return next(iter)

def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

def launch_containers(new_container):

    container_name = f"server_{new_container+1}"
    IP_third_octet = 3 + new_container

    if IP_third_octet == 100:
        return 1

    # The commands to start the creation of a new container

    docker_run_cmd_list = ["docker", "run", "-it", "-d", "--privileged",
            "--net", "migrate-net",  "--ip", f"172.20.0.{IP_third_octet}",
            "-v", "socket_migration_volume:/migvolume1", "--name", container_name, 
            "--hostname", container_name, "server"]
    # subprocess.call(args=docker_run_cmd_list, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null", shell=False)
    subprocess.call(args=docker_run_cmd_list)

    # docker_exec_list = ["docker", "exec", "server_2", "service", "ssh", "start"]
    # subprocess.call(docker_exec_list)

    # docker_exec_list = ["docker", "exec", "server_2", "bash", "-c", "'/usr/bin/python single/echo_threading.py --ip=172.20.0.4 &'"]
    docker_exec_list_2 = ["docker", "exec", container_name, "/bin/bash", "/root/run_server.sh", f"172.20.0.{IP_third_octet}", f"/migvolume1/logs/{container_name}.log"]
    subprocess.call(args=docker_exec_list_2)

    # TODO: Here we should also launch the C program that dumps the sockets.

    return 1

class LoadBalancer(object):
    """ Socket implementation of a load balancer.
    Flow Diagram:
    +---------------+      +-----------------------------------------+      +---------------+
    | client socket | <==> | client-side socket | server-side socket | <==> | server socket |
    |   <client>    |      |          < load balancer >              |      |    <server>   |
    +---------------+      +-----------------------------------------+      +---------------+
    Attributes:
        ip (str): virtual server's ip; client-side socket's ip
        port (int): virtual server's port; client-side socket's port
        algorithm (str): algorithm used to select a server
        flow_table (dict): mapping of client socket obj <==> server-side socket obj
        sockets (list): current connected and open socket obj
    """

    flow_table = dict()
    sockets = list()
    migration_flow_table = dict()
    migration_sockets = list()

    # client_socket = None

    MIGRATION_TIMES = 1
    migration_counter = 0

    migration_triggered = False

    # def __init__(self, sock, client_socket_local, algorithm='random'):
    def __init__(self, ip, port, algorithm='random'):
        global MIG_PORTS
        global MIG_SERVER_POOL

        self.ip = ip
        self.port = port

        self.algorithm = algorithm

        # init a client-side socket
        # self.cs_socket = sock
        
        self.cs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # the SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state,
        # without waiting for its natural timeout to expire.
        self.cs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.cs_socket.bind((self.ip, self.port))

        logging.info(f"init client-side socket: {self.cs_socket.getsockname()}")
        self.cs_socket.listen(1000) # max connections
        self.sockets.append(self.cs_socket)

        self.lock = threading.Lock()
        
        # This will be a match of UUIDs and socket objects
        self.client_sockets_track = dict()

        # we will assign and use the migration ports based on the number of servers.
        # for index, server in enumerate(MIG_SERVER_POOL):
        #     MIG_PORTS.append(4000+index)
        MIG_PORTS.append(4001)


    def start(self):
        while True:
            read_list, write_list, exception_list = select.select(self.sockets, [], [])
            for sock in read_list:
                # new connection
                if sock == self.cs_socket:
                    logging.info('='*40+'flow start'+'='*39)
                    client_socket, client_addr = self.cs_socket.accept()
                    thread = threading.Thread(target=self.on_accept, args=(client_socket, client_addr))
                    thread.start()
                    thread.join()
                    # self.on_accept()
                    break
                # incoming message from a client socket
                else:
                    try:
                        # In Windows, sometimes when a TCP program closes abruptly,
                        # a "Connection reset by peer" exception will be thrown
                        data = sock.recv(4096) # buffer size: 2^n
                        # data = sock.recv(16)
                        if data:
                            if sock.getpeername()[0] not in IPs:
                                # We add the UUID only to the clients, this wha we want to track.
                                thread = threading.Thread(target=self.on_recv, args=(sock, data, uuid.uuid4()))
                                thread.start()
                                thread.join()
                                # self.on_recv(sock, data)
                            else:
                                logging.debug("=====IN=======")
                                thread = threading.Thread(target=self.on_recv, args=(sock, data, uuid.uuid4()))
                                # thread = threading.Thread(target=self.on_recv, args=(sock, data, None))
                                thread.start()
                                # thread.join()
                        # else:
                            # # TODO: we might want to add the backend server connections
                            # # to the dict() as well
                            # if sock.getpeername()[0] not in IPs:
                            #     thread = threading.Thread(target=self.on_close, args=(sock,))
                            #     # self.clients_threads[sock] = thread
                            #     thread.start()
                            #     thread.join()
                            #     break
                            #     # self.on_close(sock)
                            #     # break

                            # else:
                            #     self.on_close(sock)
                            #     break
                    except ConnectionResetError as ex:
                        logging.error(f"ConnectionResetError {ex}")                        
                        # continue
                        break
                    except OSError as ex:
                        # print(f"OSError {ex}")
                        # continue
                        break
                    except Exception as ex:
                        logging.error(ex)
                        sock.on_close(sock)
                        break

    def on_accept(self, client_socket, client_addr):
        # client_socket, client_addr = self.cs_socket.accept()

        # NOTE: Shall we do not open any downstream connections when we receive connection from the backend servers?

        logging.info(f"{threading.current_thread().name} client connected: {client_addr} <==> {self.cs_socket.getsockname()}")
        # logging.debug(f"{threading.current_thread().name}Active Thread Count: {threading.active_count()}")

        # select a server that forwards packets to
        server_ip, server_port = self.select_server(SERVER_POOL, self.algorithm)

        if client_addr[0] not in IPs:
            # init a server-side socket
            ss_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ss_socket.settimeout(0.1)
            try:
                ss_socket.connect((server_ip, server_port))
                logging.info(f"{threading.current_thread().name} init server-side socket: {ss_socket.getsockname()}")
                logging.info(f"{threading.current_thread().name} server connected: {ss_socket.getsockname()} <==> {(socket.gethostbyname(server_ip), server_port)}")
            except:
                logging.info(f"Can't establish connection with remote server, err: {sys.exc_info()[0]}")
                logging.info(f"Closing connection with client socket {client_addr}")
                client_socket.close()
                return

        # client_socket.settimeout(0.1)
        client_socket.setblocking(0)

        self.sockets.append(client_socket)
        if client_addr[0] not in IPs:
            self.sockets.append(ss_socket)

            self.flow_table[client_socket] = ss_socket
            self.flow_table[ss_socket] = client_socket

        # self.__client_socket = client_socket

        return

    
    def on_recv(self, sock, data, unique_id):
        global IPs
        
        global MIG_SERVER_POOL
        global MIG_PORTS

        global SPAWNED_CONTAINERS

        global logs_path

        socket_id = None

        new_sock = None
        mig_data = None

        logging.info(f"recving packets: {sock.getpeername()} ==> {sock.getsockname()}, data: {data}")
        # data can be modified before forwarding to server
        # lots of add-on features can be added here

        try:
            remote_socket = self.flow_table[sock]
        except KeyError as e:
            logging.error(f"FLOWS KEY ERROR")

        # Check for clients that we need to migrate/handle connections
        if sock.getpeername()[0] not in IPs:
            remote_socket = self.flow_table[sock]  

            # Add the UUID to the dictionary along with the sock
            # to keep track of migrations if id not not exist before (i.e. active connection)
            if sock not in self.client_sockets_track.values():
                socket_id = str(unique_id)
                self.client_sockets_track[socket_id] = sock
            else:
                temp_list_values = list(self.client_sockets_track.values())
                temp_list_keys = list(self.client_sockets_track.keys())
                socket_id_position = temp_list_values.index(sock)
                socket_id = temp_list_keys[socket_id_position]

            # logging.debug(f"{threading.current_thread().name} {self.client_sockets_track}")

        # NOTE: here we should check whether we migrate based on our algo
        # that will give us a list of client IPs to migrate. For now I leave the hardcoded IP
        # This shoulde be a signal from the "agent" that lives in the backend server.
        
        # if sock.getpeername()[0] == "172.20.0.5":
        if (data.find("threads_full".encode()) != -1):
            
            # ==============================SPAWNING NEW CONTAINERS====================

            
            # if SPAWNED_CONTAINERS == 1: # Initially we have 1 container only
            #     SPAWNED_CONTAINERS = 2
            # elif (SPAWNED_CONTAINERS % 2) == 0: # then for each one container we are creating 2 more
            #     SPAWNED_CONTAINERS *= 2

            # # SPAWNED_CONTAINERS = 49
            # SPAWNED_CONTAINERS = 24

            timeStarted = time.time()
            
            results = []
            new_containers = range(1, SPAWNED_CONTAINERS+1)

            # for new_container in range(1, SPAWNED_CONTAINERS+1):
                
            #     new_spawn_thread = threading.Thread(target = self.launch_containers, args = (new_container,))
            #     # checkpoint_threads.append(new_checkpoint_thread)
            #     new_spawn_thread.start()
            #     # new_spawn_thread.join()

            # try:
            #     pool = multiprocessing.Pool()
            #     outputs_async = pool.map_async(launch_containers, new_containers)
            #     results = outputs_async.get()
            # except Exception as e:
            #     logging.error(f"POOL: {e}")

            # if (all(result == 1 for result in results)):
            #     timeDelta = time.time() - timeStarted

            # # timeDelta = time.time() - timeStarted
            # logging.info(f"{threading.current_thread().name} TIME TO RUN CONTAINERS {timeDelta}")
            # metrics_logger_SPAWN = setup_logger('metrics_logger_SPAWN', logs_path)
            # metrics_logger_SPAWN.info(f'TIME TO RUN {SPAWNED_CONTAINERS} CONTAINERS: {timeDelta}')

            # return
             
            socket_id = data.decode().split("$",2)[1]

            # mig_data = f"migration${socket_id}$\r\n\r\n".encode()
            mig_data = f"migration${socket_id}$\n".encode()
            logging.debug(f"{threading.current_thread().name} migration counter is {self.migration_counter} ...")
            logging.debug(f"{threading.current_thread().name} client sock will be {sock.getsockname()} --> {sock.getpeername()}")

            if (sock.getpeername()[0], 80) in SERVER_POOL:
                index = list(SERVER_POOL).index((sock.getpeername()[0], 80))
                new_port = MIG_PORTS[index]
                MIG_PORTS[index] = new_port+1

                logging.debug(f"New port {new_port}")
                # sys.exit(1)

            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.settimeout(0.1)
            new_sock.bind(('172.20.0.2', new_port))
            new_sock.connect((sock.getpeername()[0], 80))


            # Since we are opening connections outside of the on_accept() we need the following
            self.sockets.append(new_sock)
            self.sockets.append(sock)

            self.flow_table[new_sock] = sock
            self.flow_table[sock] = new_sock

            # self.sockets.remove(sock)
            
            # sock.close()
            # self.sockets.remove(sock)
            # new_sock.send(mig_data)

            # self.migration_sockets.append(new_sock)

            remote_socket = new_sock

            # remote_socket.send(mig_data)
            # remote_socket.send("threads_full".encode())
            logging.debug(f"{threading.current_thread().name} 2 sending packets: {new_sock.getsockname()} ==> {new_sock.getpeername()}, data: {mig_data}")

            # TODO: THIS IS A STUPID WAY FOR TESTING ***REMOVE***
            # self.migration_counter = self.MIGRATION_TIMES

            # return
        
        if (data.find("migration".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
        # if (data.find("migration".encode()) != -1):
            
            logging.debug(f"{threading.current_thread().name} Here 1")
            logging.debug(f"{threading.current_thread().name} migration counter is {self.migration_counter} ...")

            # Let's remove and close the connection with the 400* port
            # self.sockets.remove(sock)
            # sock.close()
            # del self.flow_table[sock]

            socket_ids = re.findall("\\$(.+?)\\$", data.decode())
            dumped_file_pref = re.findall("\\@(.+?)\\@", data.decode())

            # socket_id = data.decode().split("$",2)[1]
            dumped_sockets_num = len(socket_ids)

            # NOTE: we hardcode it for now
            next_server = round_robin(MIG_ITER)
            # next_server = ("172.20.0.4", 80)

            results = []

            try:
                # +1 is for the migration signal. NOTE: Do we really need it?
                # TODO: Can that loop happen in parallel?
                # for dumped_sock in range(int(dumped_sockets_num)+1):
                
                timeStarted = time.time()

                for dumped_sock_num in range(int(dumped_sockets_num)):

                    new_restore_thread = threading.Thread(target = self.restore_signal, args = (sock, socket_ids, dumped_file_pref,  dumped_sock_num, next_server ,results))
                    # checkpoint_threads.append(new_checkpoint_thread)
                    new_restore_thread.start()
                    new_restore_thread.join()

                if (all(result == 1 for result in results)):
                    timeDelta = time.time() - timeStarted
                    metrics_logger_restore = setup_logger('metrics_logger_restore', logs_path)
                    metrics_logger_restore.info(f'Restore time for {dumped_sockets_num} connection (parallel): {timeDelta}')

                    # self.migration_counter += 1
                else:
                    logging.debug(f"{threading.current_thread().name} Not all sockets dumped, investigate")
                    os._exit(-1)

                return
            except ValueError as err:
                    logging.error(err)
        

        if (data.find("mig_signal_2".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
            # NOTE: If we do it this way, we mean only dumping and restore to another machine
            logging.debug(f"{threading.current_thread().name} Here 2")
            self.migration_counter += 1

        # if (data.find("mig_signal_2".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
        # # elif (data.find("mig_signal_2".encode()) != -1):
        #     logging.debug(f"{threading.current_thread().name} Here 2")

        #     # NOTE Not sure if this one should be here.
        #     self.migration_counter += 1

        #     socket_id = data.decode().split("$",2)[1]

        #     new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #     new_sock.settimeout(0.1)
        #     new_sock.connect((sock.getpeername()[0], 80))

        #     self.sockets.append(new_sock)
        #     self.sockets.append(sock)

        #     self.flow_table[new_sock] = sock
        #     self.flow_table[sock] = new_sock

        #     remote_socket = new_sock

        #     logging.debug(f"{threading.current_thread().name} New 2 {new_sock.getsockname()} with {new_sock.getpeername()}")

        #     # TODO: Need to find a way that both N migrations can happen but also send correct
        #     # messages and do not stuck in a loop (more checks and send outside the if statments?)
            
        #     mig_data = f"migration_ZZZ${socket_id}$\n".encode()

        # TODO: Maybe here we should check for the mig_signal_2 as well? (or just for that?)
        if (self.migration_counter == self.MIGRATION_TIMES) and (data.find("$".encode()) != -1):
        # if (self.migration_counter == self.MIGRATION_TIMES) and (data.find("$".encode()) != -1) and (data.find("mig_signal_2".encode()) != -1):
            self.migration_counter = 0

            logging.debug(f"{threading.current_thread().name} Here 3")       

            # socket_id = data.decode().split(":",2)[1]
            socket_id = data.decode().split("$",2)[1]
            dumped_sockets_num = data.decode().split("@",2)[1]

            remote_socket = self.client_sockets_track[socket_id]

            data = data.decode().replace(f"${socket_id}$", "")
            data = data.replace(f"@{dumped_sockets_num}@", "")
            # data = f"HTTP/1.1 200 OK\n\nContent-Length: {len(data)}\n\nContent-Type: text/plain\n\nConnection: Closed\n\n{data.encode()}"
            data = data.encode()
            
            # TODO: The follwing send or the one outside the if-else is probably redundant and can be removed
            logging.info(f"sending packets: {remote_socket.getsockname()} ==> {remote_socket.getpeername()}, data: {data}")
            remote_socket.send(data)
            
            return

        # else:
        #     new_sock.send(mig_data)
            
        #     self.sockets.append(new_sock)
        #     self.migration_sockets.append(new_sock)

        #     self.flow_table[new_sock] = new_sock
        #     return

            
        # remote_socket.send(data)
        # data = "migration".encode()
        
        # remote_socket.send(f"HTTP/1.1 200 OK\n\nContent-Length: {len(data)}\n\nContent-Type: text/plain\n\nConnection: Closed\n\n{data.decode()}".encode())
        if socket_id == None:
            # remote_socket.send(f"HTTP/1.1 200 OK\n\nContent-Length: {len(data)}\n\nContent-Type: text/plain\n\nConnection: Closed\n\n{data.decode()}".encode())
            remote_socket.send(f"{data.decode()}".encode())
            logging.info(f"sending packets: {remote_socket.getsockname()} ==> {remote_socket.getpeername()}, data: {data}")
        else:
            if mig_data != None:
                remote_socket.send(mig_data)
                logging.info(f"sending packets: {remote_socket.getsockname()} ==> {remote_socket.getpeername()}, data: {mig_data}")
            else:
                remote_socket.send(f"${socket_id}${data.decode()}".encode())
                # remote_socket.send(f"{data.decode()}".encode())
                logging.info(f"sending packets: {remote_socket.getsockname()} ==> {remote_socket.getpeername()}, data: {data}")
        
        # return


    def on_close(self, sock):
        logging.info(f"client {sock.getpeername()} has disconnected")
        logging.info('='*41+'flow end'+'='*40)

        # NOTE: Is the first check really needed?
        if sock.getpeername()[0] not in IPs:
            socket_id = {sock_id for sock_id in self.client_sockets_track if self.client_sockets_track[sock_id] == sock}
            if socket_id != set():
                # print(socket_id)
                del self.client_sockets_track[next(iter(socket_id))]

        ss_socket = self.flow_table[sock]

        self.sockets.remove(sock)

        if sock not in self.migration_sockets: 
            self.sockets.remove(ss_socket)

        sock.close()  # close connection with client
        ss_socket.close()  # close connection with server
        del self.flow_table[sock]
        if sock not in self.migration_sockets: 
            del self.flow_table[ss_socket]

    def select_server(self, server_list, algorithm):
        if algorithm == 'random':
            return random.choice(server_list)
        elif algorithm == 'round robin':
            return round_robin(ITER)
        else:
            raise Exception('unknown algorithm: %s' % algorithm)

    def restore_signal(self, sock, socket_ids, dumped_file_pref, dumped_sock, next_server, results):
        try:
            # self.migration_counter += 1
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # NOTE: Use the existing round robin to move to the next server that we want to migrate to.
            new_sock.settimeout(0.1)
            new_sock.connect(next_server)
            
            logging.debug(f"{threading.current_thread().name} New {new_sock.getsockname()} with {new_sock.getpeername()}")

            self.sockets.append(new_sock)
            self.sockets.append(sock)

            self.flow_table[new_sock] = sock
            self.flow_table[sock] = new_sock

            # NOTE: This is a naive way to send a second signal to the entity that will retrieve
            # the migration data (can be anything, just make two distinct operations, dump/restore)
            # mig_data = f"mig_signal_2${socket_id}$\r\n\r\n".encode()
            mig_data = f"mig_signal_2${socket_ids[dumped_sock]}$@{dumped_file_pref[dumped_sock]}@\n".encode()

            # NOTE: We do not go to the if statements below here since we have to do that recursively for all the dumped sockets.
            remote_socket = new_sock
            remote_socket.send(f"{mig_data.decode()}".encode())
            logging.info(f"sending packets: {remote_socket.getsockname()} ==> {remote_socket.getpeername()}, data: {mig_data}")

            results.append(1)
        except Exception as e:
            logging.error(f"Connection_Restore {e}")
            results.append(-1)

        return

    # def launch_containers(self, new_container):
    #     # timeStarted = time.time()

    #     container_name = f"server_{new_container+1}"
    #     IP_third_octet = 3 + new_container

    #     # The commands to start the creation of a new container

    #     docker_run_cmd_list = ["docker", "run", "-it", "-d", "--privileged",
    #             "--net", "migrate-net",  "--ip", f"172.20.0.{IP_third_octet}",
    #             "-v", "socket_migration_volume:/migvolume1", "--name", container_name, 
    #             "--hostname", container_name, "server"]
    #     # subprocess.call(args=docker_run_cmd_list, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null", shell=False)
    #     subprocess.call(args=docker_run_cmd_list)
    #     # try:
    #     #     subprocess.check_call(args=docker_run_cmd_list)
    #     # except subprocess.CalledProcessError:
            
        

    #     # docker_exec_list = ["docker", "exec", "server_2", "service", "ssh", "start"]
    #     # subprocess.call(docker_exec_list)

    #     # docker_exec_list = ["docker", "exec", "server_2", "bash", "-c", "'/usr/bin/python single/echo_threading.py --ip=172.20.0.4 &'"]
    #     docker_exec_list_2 = ["docker", "exec", container_name, "/bin/bash", "/root/run_server.sh", f"172.20.0.{IP_third_octet}", f"/migvolume1/logs/{container_name}.log"]
    #     subprocess.call(args=docker_exec_list_2)

    #     # TODO: Here we should also launch the C program that dumps the sockets.
    #     # logging.info(f"Container {new_container}: {time.time()-timeStarted}")
    #     return


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-logsPath", "--logsPath", dest = "logs_path", help = "Define a path for logs storage")
    options = parser.parse_args()

    return options


def main():

    global logs_path

    options = get_args()
    logs_path = options.logs_path

    try:
        # LoadBalancer('localhost', 5555, 'round robin').start()
        LoadBalancer('172.20.0.2', 80, 'round robin').start()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping load_balancer")
        sys.exit(1)

if __name__ == '__main__':
    main()
