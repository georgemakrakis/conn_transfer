# From: https://gist.github.com/zhouchangxun/5750b4636cc070ac01385d89946e0a7b

import sys, logging
import socket
import select
import random, uuid
from itertools import cycle
import threading

import struct, array, time

# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done
SERVER_POOL = [('172.20.0.3', 80)]
# SERVER_POOL = [('172.20.0.3', 80), ('172.20.0.4',80)]
# SERVER_POOL = [('172.20.0.3', 80), ('172.20.0.4',80), ('172.20.0.7', 80)]

MIG_SERVER_POOL = [('172.20.0.4', 80), ('172.20.0.3', 80)]
# MIG_SERVER_POOL = [('172.20.0.4', 80), ('172.20.0.7',80), ('172.20.0.3', 80)]

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

logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)


ITER = cycle(SERVER_POOL)
MIG_ITER = cycle(MIG_SERVER_POOL) # This one is slided one step to the right as above
def round_robin(iter):
    # round_robin([A, B, C, D]) --> A B C D A B C D A B C D ...
    return next(iter)


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
        self.cs_socket.listen(10) # max connections
        self.sockets.append(self.cs_socket)

        self.lock = threading.Lock()
        
        # This will be a match of UUIDs and socket objects
        self.client_sockets_track = dict()

        # we will assign and use the migration ports based on the number of servers.
        for index, server in enumerate(SERVER_POOL):
            MIG_PORTS.append(4000+index)


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
                        # data = sock.recv(16) # buffer size: 2^n
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
                        #     # TODO: we might want to add the backend server connections
                        #     # to the dict() as well
                        #     if sock.getpeername()[0] not in IPs:
                        #         thread = threading.Thread(target=self.on_close, args=(sock,))
                        #         # self.clients_threads[sock] = thread
                        #         thread.start()
                        #         thread.join()
                        #         break
                        #         # self.on_close(sock)
                        #         # break

                        #     else:
                        #         self.on_close(sock)
                        #         break
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
             
            socket_id = data.decode().split("$",2)[1]

            # mig_data = f"migration${socket_id}$\r\n\r\n".encode()
            mig_data = f"migration${socket_id}$\n".encode()
            logging.debug(f"{threading.current_thread().name} migration {self.migration_counter} is initiated...")
            logging.debug(f"{threading.current_thread().name} client sock will be {sock.getsockname()} --> {sock.getpeername()}")

            if (sock.getpeername()[0], 80) in SERVER_POOL:
                index = list(SERVER_POOL).index((sock.getpeername()[0], 80))
                new_port = MIG_PORTS[index]
                # sys.exit(1)

            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

            # Let's remove and close the connection with the 400* port
            # self.sockets.remove(sock)
            # sock.close()
            # del self.flow_table[sock]

            socket_id = data.decode().split("$",2)[1]
        
            # self.migration_counter += 1
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # NOTE: Use the existing round robin to move to the next server that we want to migrate to.
            new_sock.connect(round_robin(MIG_ITER))

            logging.debug(f"{threading.current_thread().name} New {new_sock.getsockname()} with {new_sock.getpeername()}")

            self.sockets.append(new_sock)
            self.sockets.append(sock)

            self.flow_table[new_sock] = sock
            self.flow_table[sock] = new_sock

            # NOTE: This is a naive way to send a second signal to the entity that will retrieve
            # the migration data (can be anything, just make two distinct operations, dump/restore)
            # mig_data = f"mig_signal_2${socket_id}$\r\n\r\n".encode()
            mig_data = f"mig_signal_2${socket_id}$\n".encode()

            remote_socket = new_sock
        
            # return

        if (data.find("mig_signal_2".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
            # NOTE: If we do it this way, we mean only dumping and restore to another machine
            logging.debug(f"{threading.current_thread().name} Here 2")
            self.migration_counter += 1

        # if (data.find("mig_signal_2".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
        # # elif (data.find("mig_signal_2".encode()) != -1):
        #     logging.debug(f"{threading.current_thread().name} Here 2")

        #     self.migration_counter += 1

        #     socket_id = data.decode().split("$",2)[1]            

        #     new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
        #     new_sock.connect((sock.getpeername()[0], 80))

        #     logging.debug(f"{threading.current_thread().name} New 2 {new_sock.getsockname()} with {new_sock.getpeername()}")

        #     # NOTE: Correct data will be "migration" but "Ended" is for testing with 2 servers
        #     # and 1 migration.
        #     # NOTE: But if we send migration again, another socket dump will happen.
        #     # TODO: Need to find a way that both N migrations can happen but also send correct
        #     # messages and do not stuck in a loop (more checks and send outside the if statments?)
            
        #     mig_data = f"migration:{socket_id}:\r\n\r\n".encode()

        # TODO: Maybe here we should check for the mig_signal_2 as well? (or just for that?)
        if (self.migration_counter == self.MIGRATION_TIMES) and (data.find("$".encode()) != -1):
            self.migration_counter = 0

            logging.debug(f"{threading.current_thread().name} Here 3")       

            # socket_id = data.decode().split(":",2)[1]
            socket_id = data.decode().split("$",2)[1]

            remote_socket = self.client_sockets_track[socket_id]

            data = data.decode().replace(f"${socket_id}$", "")
            # data = f"HTTP/1.1 200 OK\n\nContent-Length: {len(data)}\n\nContent-Type: text/plain\n\nConnection: Closed\n\n{data.encode()}"
            data = data.encode()
            
            # TODO: The follwing send or the one outside the if-else is probably redundant and can be removed
            remote_socket.send(data.encode())
            logging.info(f"sending packets: {remote_socket.getsockname()} ==> {remote_socket.getpeername()}, data: {data}")
            
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
                remote_socket.send(f"{mig_data.decode()}".encode())
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


if __name__ == '__main__':
    try:
        # LoadBalancer('localhost', 5555, 'round robin').start()
        LoadBalancer('172.20.0.2', 80, 'round robin').start()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping load_balancer")
        sys.exit(1)
