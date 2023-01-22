# From: https://gist.github.com/zhouchangxun/5750b4636cc070ac01385d89946e0a7b

import sys
import socket
import select
import random
from itertools import cycle

import struct, array, time

# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done
SERVER_POOL = [('172.20.0.3', 80), ('172.20.0.4',80)]

# dumb python socket echo server, long tcp connection
# $ ~  while  python server.py
# SERVER_POOL = [('localhost', 6666)]


# IPs = ["172.20.0.3", "172.20.0.4"]
IPs = ["172.20.0.4", "172.20.0.3"]
MIGRATION_TIMES = 1
migration_counter = 0
latest_server = ""
initiated_migration = False

# Should that be a list inside the class?
client_socket = None

prev_server_socket = None

ITER = cycle(SERVER_POOL)
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


    migration_triggered = False

    def __init__(self, ip, port, algorithm='random'):
        self.ip = ip
        self.port = port
        self.algorithm = algorithm

        # init a client-side socket
        self.cs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # the SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state,
        # without waiting for its natural timeout to expire.
        self.cs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.cs_socket.bind((self.ip, self.port))
        print('init client-side socket: %s' % (self.cs_socket.getsockname(),))
        self.cs_socket.listen(10) # max connections
        self.sockets.append(self.cs_socket)

    def start(self):
        while True:
            read_list, write_list, exception_list = select.select(self.sockets, [], [])
            for sock in read_list:
                # new connection
                if sock == self.cs_socket:
                    print('='*40+'flow start'+'='*39)
                    self.on_accept()
                    break
                # incoming message from a client socket
                else:
                    try:
                        # In Windows, sometimes when a TCP program closes abruptly,
                        # a "Connection reset by peer" exception will be thrown
                        data = sock.recv(4096) # buffer size: 2^n
                        if data:
                            self.on_recv(sock, data)
                        else:
                            self.on_close(sock)
                            break
                    except ConnectionResetError as ex:
                        print(f"ConnectionResetError {ex}")                        
                        # continue
                        break
                    except OSError as ex:
                        # print(f"OSError {ex}")
                        # continue
                        break
                    except Exception as ex:
                        print(ex)
                        sock.on_close(sock)
                        break

    def on_accept(self):
        client_socket, client_addr = self.cs_socket.accept()
        print('client connected: %s <==> %s' % (client_addr, self.cs_socket.getsockname()))

        # select a server that forwards packets to
        server_ip, server_port = self.select_server(SERVER_POOL, self.algorithm)

        # init a server-side socket
        ss_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            ss_socket.connect((server_ip, server_port))
            print('init server-side socket: %s' % (ss_socket.getsockname(),))
            print('server connected: %s <==> %s' % (ss_socket.getsockname(),(socket.gethostbyname(server_ip), server_port)))
        except:
            print("Can't establish connection with remote server, err: %s" % sys.exc_info()[0])
            print("Closing connection with client socket %s" % (client_addr,))
            client_socket.close()
            return

        self.sockets.append(client_socket)
        self.sockets.append(ss_socket)

        self.flow_table[client_socket] = ss_socket
        self.flow_table[ss_socket] = client_socket

    
    def on_recv(self, sock, data):
        global IPs
        global MIGRATION_TIMES
        global migration_counter
        global latest_server
        global initiated_migration
        global client_socket
        global prev_server_socket

        print('recving packets: %-20s ==> %-20s, data: %s' % (sock.getpeername(), sock.getsockname(), [data]))
        # data can be modified before forwarding to server
        # lots of add-on features can be added here

        # Check for clients that we need to migrate/handle connections
        if sock.getpeername()[0] not in IPs:
            remote_socket = self.flow_table[sock]

        # NOTE: here we should check whether we migrate based on our algo
        # that will give us a list of client IPs to migrate. For now I leave the hardcoded IP
        if sock.getpeername()[0] == "172.20.0.5":
            data = "migration".encode()
            print(f"migration {migration_counter} is initiated...")
            client_socket = sock

            remote_socket.send(data)
            # prev_server_socket = remote_socket
            print('2 sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))
            return

        # NOTE: Hardcoded for now but this can be scaled later based on number of requests
        # if sock.getpeername()[0] == "172.20.0.3":
       
        # We also need to check the messages/signals here.    
        # if sock.getpeername()[0] == IPs[migration_counter % len(IPs)]:
        
        if (data.find("migration".encode()) != -1) and (migration_counter != MIGRATION_TIMES):
        # if (data.find("migration".encode()) != -1):
            
            print("Here 1")

            
            
            # if prev_server_socket:                
            #     prev_server_socket.close()
            #     print("Prev sock closed 1")
        
            # migration_counter += 1
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
            # NOTE: The following is a stupid way to have pre-agreed port with the other servers.
            # Not needed so we might remove it completely. Leave for now cause it is good for debugging.
            new_sock.bind(('172.20.0.2', 50630 + migration_counter))
            new_sock.connect((IPs[((migration_counter) % len(IPs))], 80))
            print(f'New {new_sock.getsockname()} with {new_sock.getpeername()}')

            # NOTE: This is a naive way to send a second signal to the entitry that will retrieve
            # the migration data (can be anything)
            new_sock.send("mig_signal_2".encode())
            
            self.sockets.append(new_sock)
            self.migration_sockets.append(new_sock)

            self.flow_table[new_sock] = new_sock
            # self.flow_table[ss_socket] = client_socket


            prev_server_socket = new_sock

            # TODO: Need to keep track of these things to close them later on.
            # self.migration_flow_table[new_sock] = (new_sock_2, client_socket)
            # self.migration_flow_table[new_sock_2] = (new_sock_2, client_socket)

            # We want to close the socket that send us the data
            # sock.close()

            return
            
        # elif (data.find("mig_signal_2".encode()) != -1) and (migration_counter != MIGRATION_TIMES):
        elif (data.find("mig_signal_2".encode()) != -1):
            print("Here 2")

            # if prev_server_socket:                
            #     prev_server_socket.close()
            #     print("Prev sock closed 2")

            new_sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock_2.connect((IPs[((migration_counter) % len(IPs))], 80))
            print(f'New {new_sock_2.getsockname()} with {new_sock_2.getpeername()}')

            # new_sock_2 = self.migration_flow_table[sock][0]
            data = "migration".encode()
            new_sock_2.send(data)

            migration_counter += 1

            self.sockets.append(new_sock_2)
            self.migration_sockets.append(new_sock_2)

            # print(f"NEW SOCK {new_sock_2.getsockname()} --> {new_sock_2.getpeername()}")
            # self.flow_table[new_sock_2] = new_sock_2

            prev_server_socket = new_sock_2

            # sock.close()

            return

        else:
            # remote_socket = self.migration_flow_table[sock][1] 
            # prev_server_socket.close()
            print("Here 3")       
            remote_socket = client_socket

        if migration_counter == MIGRATION_TIMES:
            migration_counter = 0          

            
        remote_socket.send(data)
        print('sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))
        # migration_counter = 0


    def on_close(self, sock):
        print('client %s has disconnected' % (sock.getpeername(),))
        print('='*41+'flow end'+'='*40)

        # if (sock.getpeername()[0] in IPs):
        #     self.sockets.remove(sock)
        #     sock.close()
        #     return

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
        LoadBalancer('0.0.0.0', 80, 'round robin').start()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping load_balancer")
        sys.exit(1)