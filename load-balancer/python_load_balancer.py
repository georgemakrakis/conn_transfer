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


IPs = ["172.20.0.3", "172.20.0.4"]
MIGRATION_TIMES = 5
migration_counter = 0
latest_server = ""
initiated_migration = False

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
                    except:
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

        print('recving packets: %-20s ==> %-20s, data: %s' % (sock.getpeername(), sock.getsockname(), [data]))
        # data can be modified before forwarding to server
        # lots of add-on features can be added here
        remote_socket = self.flow_table[sock]

        # NOTE: here we should check whether we migrate based on our algo
        # that will give us a list of client IPs to migrate. For now I leave the hardcoded IP
        if sock.getpeername()[0] == "172.20.0.5":
            data = "migration".encode()
            print(f"migration {migration_counter} is initiated...")

        # NOTE: Hardcoded for now but this can be scaled later based on number of requests
        # if sock.getpeername()[0] == "172.20.0.3":
       
            
        if sock.getpeername()[0] == IPs[migration_counter % len(IPs)]:
            

            print("Here")

            new_socks = []
            for i in range(MIGRATION_TIMES):
                migration_counter += 1
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                #new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                # NOTE: The following is a stupid way to have pre-agreed port with the other servers
                new_sock.bind(('172.20.0.2', 50630 + migration_counter))
                new_sock.connect((IPs[((migration_counter) % len(IPs))], 80))
                print(f'New {new_sock.getsockname()}')

                # NOTE: This is a naive way to send a second signal to the entitry that will retrieve
                # the migration data (can be anything)
                new_sock.send("mig_signal_2".encode())

                # time.sleep(25)
                
                response = new_sock.recv(4096)
                # if response:
                #     data = response
                
                # print(f"Proxy received data {response.decode()}")
                new_sock.close()

                new_sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_sock_2.connect((IPs[((migration_counter) % len(IPs))], 80))
                data = "migration".encode()
                new_sock_2.send(data)
                response = new_sock_2.recv(4096)
                if response:
                    data = response
                    print(f"BBB {response.decode()}")
                print(f"migration {migration_counter + 1 } is initiated...")

                # migration_counter += 1 # Should that go on the top after the FOR?

                # return
                
            # TODO: To generalize the above we need to have some steps that
            # will do the migration between machines N-times
            # will keep track of the IP that had the latest migration,
            # the signals names that indicate that the recovery of the socket 
            # will take place.
            # When all the migrations have taken place, we send the data back
            # to the client.
            # TODO: We also need to add the counter to each request to show the
            # correct number of migrations between machines
            
        remote_socket.send(data)
        print('sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))
        # migration_counter = 0


    def on_close(self, sock):
        print('client %s has disconnected' % (sock.getpeername(),))
        print('='*41+'flow end'+'='*40)

        ss_socket = self.flow_table[sock]

        self.sockets.remove(sock)
        self.sockets.remove(ss_socket)
        

        sock.close()  # close connection with client
        ss_socket.close()  # close connection with server
        del self.flow_table[sock]
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