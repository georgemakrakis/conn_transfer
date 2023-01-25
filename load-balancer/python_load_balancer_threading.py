# From: https://gist.github.com/zhouchangxun/5750b4636cc070ac01385d89946e0a7b

import sys
import socket
import select
import random
from itertools import cycle
import threading

import struct, array, time

# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done
SERVER_POOL = [('172.20.0.3', 80), ('172.20.0.4',80)]

# dumb python socket echo server, long tcp connection
# $ ~  while  python server.py
# SERVER_POOL = [('localhost', 6666)]

# TODO: See if we can reuse the above array of tuples
# IPs = ["172.20.0.3", "172.20.0.4"]
IPs = ["172.20.0.4", "172.20.0.3"]
# MIGRATION_TIMES = 2
# migration_counter = 0
latest_server = ""
initiated_migration = False

# Should that be a list inside the class?
# client_socket = None



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

    # client_socket = None

    MIGRATION_TIMES = 1
    migration_counter = 0


    migration_triggered = False

    # def __init__(self, ip, port, algorithm='random'):
    #     self.ip = ip
    #     self.port = port
    #     self.algorithm = algorithm

    #     # init a client-side socket
    #     self.cs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     # the SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state,
    #     # without waiting for its natural timeout to expire.
    #     self.cs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #     self.cs_socket.bind((self.ip, self.port))
    #     print('init client-side socket: %s' % (self.cs_socket.getsockname(),))
    #     self.cs_socket.listen(10) # max connections
    #     self.sockets.append(self.cs_socket)

    # def __init__(self, sock, client_socket_local, algorithm='random'):
    def __init__(self, ip, port, algorithm='random'):
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

        print('init client-side socket: %s' % (self.cs_socket.getsockname(),))
        self.cs_socket.listen(10) # max connections
        self.sockets.append(self.cs_socket)

        # self.__client_socket = client_socket_local

        self.lock = threading.Lock()

        self.clients_threads = dict()

    def start(self):
        while True:
            read_list, write_list, exception_list = select.select(self.sockets, [], [])
            for sock in read_list:
                # new connection
                if sock == self.cs_socket:
                    print('='*40+'flow start'+'='*39)
                    thread = threading.Thread(target=self.on_accept())
                    # TODO: Change the name to connection_threads
                    # self.clients_threads[sock] = thread
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
                        if data:
                            print("BBBBB clients_threads")
                            print(self.clients_threads)
                            thread_id = self.clients_threads[sock]
                            if not any(th.ident == thread_id for th in threading.enumerate()):
                                thread = threading.Thread(target=self.on_recv, args=(sock, data))
                                
                                thread.start()
                                thread.join()
                            # self.on_recv(sock, data)
                        else:
                            thread_id = self.clients_threads[sock]
                            if not any(th.ident == thread_id for th in threading.enumerate()):
                                thread = threading.Thread(target=self.on_close, args=(sock))
                                self.clients_threads[sock] = thread
                                thread.start()
                                thread.join()
                                break
                            # self.on_close(sock)
                            # break
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

        self.clients_threads[client_socket] = threading.get_ident()

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

        self.__client_socket = client_socket
        # self.client_socket = threading.local()

        # self.client_socket.value = client_socket
        # client_socket_glob.value = client_socket

    
    def on_recv(self, sock, data):

        # global client_socket_glob

        global IPs
        # global MIGRATION_TIMES
        # global migration_counter
        global latest_server
        global initiated_migration
        # global client_socket
        global prev_server_socket

        print('recving packets: %-20s ==> %-20s, data: %s' % (sock.getpeername(), sock.getsockname(), [data]))
        # data can be modified before forwarding to server
        # lots of add-on features can be added here

        # Check for clients that we need to migrate/handle connections
        if sock.getpeername()[0] not in IPs:
            remote_socket = self.flow_table[sock]
            print("REMOTE SOCK SET!!!")
            # self.client_socket = sock

            # client_socket_glob.value = sock

        # NOTE: here we should check whether we migrate based on our algo
        # that will give us a list of client IPs to migrate. For now I leave the hardcoded IP
        if sock.getpeername()[0] == "172.20.0.5":
            data = "migration".encode()
            print(f"migration {self.migration_counter} is initiated...")
            # self.client_socket = sock
            # print(f"client sock will be {self.client_socket.getsockname()} --> {self.client_socket.getpeername()}")
            print(f"client sock will be {sock.getsockname()} --> {sock.getpeername()}")

            remote_socket.send(data)
            # prev_server_socket = remote_socket
            print('2 sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))
            return

        # NOTE: Hardcoded for now but this can be scaled later based on number of requests
        # if sock.getpeername()[0] == "172.20.0.3":
       
        # We also need to check the messages/signals here.    
        # if sock.getpeername()[0] == IPs[migration_counter % len(IPs)]:
        
        if (data.find("migration".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
        # if (data.find("migration".encode()) != -1):
            
            print("Here 1")

            
            
            # if prev_server_socket:                
            #     prev_server_socket.close()
            #     print("Prev sock closed 1")
        
            # migration_counter += 1
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
            # NOTE: The following is a stupid way to have pre-agreed port with the other servers.
            # Not needed so we might remove it completely. Leave for now cause it is good for debugging.
            # new_sock.bind(('172.20.0.2', 50630 + self.migration_counter))
            
            new_sock.connect((IPs[((self.migration_counter) % len(IPs))], 80))
            print(f'New {new_sock.getsockname()} with {new_sock.getpeername()}')

            # NOTE: This is a naive way to send a second signal to the entitry that will retrieve
            # the migration data (can be anything)
            new_sock.send("mig_signal_2".encode())
            
            self.sockets.append(new_sock)
            self.migration_sockets.append(new_sock)

            self.flow_table[new_sock] = new_sock
            # self.flow_table[ss_socket] = client_socket        


            prev_server_socket = new_sock

            # print(f"1 client sock is {self.client_socket.getsockname()} --> {self.client_socket.getpeername()}")

            # TODO: Need to keep track of these things to close them later on.
            # self.migration_flow_table[new_sock] = (new_sock_2, client_socket)
            # self.migration_flow_table[new_sock_2] = (new_sock_2, client_socket)

            # We want to close the socket that send us the data
            # sock.close()

            return
            
        elif (data.find("mig_signal_2".encode()) != -1) and (self.migration_counter != self.MIGRATION_TIMES):
        # elif (data.find("mig_signal_2".encode()) != -1):
            print("Here 2")

            # if prev_server_socket:                
            #     prev_server_socket.close()
            #     print("Prev sock closed 2")

            new_sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock_2.connect((IPs[((self.migration_counter) % len(IPs))], 80))
            print(f'New 2 {new_sock_2.getsockname()} with {new_sock_2.getpeername()}')

            # new_sock_2 = self.migration_flow_table[sock][0]
            data = "migration".encode()
            new_sock_2.send(data)

            self.migration_counter += 1

            self.sockets.append(new_sock_2)
            self.migration_sockets.append(new_sock_2)

            # print(f"NEW SOCK {new_sock_2.getsockname()} --> {new_sock_2.getpeername()}")
            # self.flow_table[new_sock_2] = new_sock_2

            prev_server_socket = new_sock_2

            # print(f"2 client sock is {self.client_socket.getsockname()} --> {self.client_socket.getpeername()}")

            # sock.close()

            return

        else:
            # remote_socket = self.migration_flow_table[sock][1] 
            # prev_server_socket.close()
            print("Here 3")       
            # print(f"client sock is {self.client_socket.getsockname()} --> {self.client_socket.getpeername()}")
            # remote_socket = self.client_socket.value
            # remote_socket = client_socket_glob.value
            remote_socket = self.__client_socket

            print("Printing all sockets")
            for so in self.sockets:
                print(so)
            
            print(f"CURRENT THREAD {threading.get_ident()}")

            remote_socket.send(f"HTTP/1.1 200 OK\n\nContent-Length: {len(data)}\n\nContent-Type: text/plain\n\nConnection: Closed\n\n{data.decode()}".encode())
            print('sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))

        if self.migration_counter == self.MIGRATION_TIMES:
            self.migration_counter = 0          

            
        # remote_socket.send(data)
        # remote_socket.send(f"HTTP/1.1 200 OK\n\nContent-Length: {len(data)}\n\nContent-Type: text/plain\n\nConnection: Closed\n\n{data.decode()}".encode())
        # print('sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))
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
        LoadBalancer('172.20.0.2', 80, 'round robin').start()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping load_balancer")
        sys.exit(1)

# Create ONE socket.
# addr = ('172.20.0.2', 80)
# LB_sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
# LB_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# LB_sock.bind(addr)
# LB_sock.listen(10)

# Launch N listener threads.
# class Thread(threading.Thread):
#     def __init__(self, i, client_socket):
#         threading.Thread.__init__(self)
#         self.i = i
#         self.daemon = True
#         self.client_socket = client_socket
#         # self.start()        
#     def run(self):
#     #     httpd = http.server.HTTPServer(addr, Handler, False)

#     #     # Prevent the HTTP server from re-binding every handler.
#     #     # https://stackoverflow.com/questions/46210672/
#     #     httpd.socket = sock
#     #     httpd.server_bind = self.server_close = lambda self: None

#     #     httpd.serve_forever()
#         # LoadBalancer('172.20.0.2', 80, 'round robin').start()
#         LoadBalancer(LB_sock, self.client_socket, 'round robin').start()


# [Thread(i) for i in range(10)]
# for i in range(10):
#     thread = Thread(i, threading.local())
#     # print(thread)
#     thread.start()

# client_socket_glob = threading.local()
# # client_socket_local = threading.local()

# for i in range(5):
#     # a = LoadBalancer(LB_sock, client_socket_local, 'round robin')
#     a = LoadBalancer(LB_sock, None, 'round robin')
#     t = threading.Thread(target=a.start(), daemon=True)
#     t.start()
#     # t.join()

# time.sleep(9e9)