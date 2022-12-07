# From: https://gist.github.com/zhouchangxun/5750b4636cc070ac01385d89946e0a7b

import sys
import socket
import select
import random
from itertools import cycle

import struct, array
from scapy import *

class TCPPacket:
    def __init__(self,
                 src_host,
                 src_port,
                 dst_host,
                 dst_port,
                 flags=0,
                 data=None):
        self.src_host = src_host
        self.src_port = src_port
        self.dst_host = dst_host
        self.dst_port = dst_port
        self.flags = flags
        self.data = data

    @staticmethod
    def get_chksum(packet):
        if len(packet) % 2 != 0:
            packet += b'\0'
        res = sum(array.array("H", packet))
        res = (res >> 16) + (res & 0xffff)
        res += res >> 16
        return (~res) & 0xffff

    def build(self):
        packet = struct.pack(
            '!HHIIBBHHH',
            self.src_port,  # Source Port
            self.dst_port,  # Destination Port
            0,              # Sequence Number
            0,              # Acknoledgement Number
            5 << 4,         # Data Offset
            self.flags,     # Flags
            8192,           # Window
            0,              # Checksum (initial value)
            0,               # Urgent pointer
        )
        pseudo_hdr = struct.pack(
           '!4s4sHH',
            socket.inet_aton(self.src_host),    # Source Address
            socket.inet_aton(self.dst_host),    # Destination Address
            socket.IPPROTO_TCP,                 # Protocol ID
            len(packet)                         # TCP Length
        )

        final_pak = b''.join([pseudo_hdr,packet, self.data])
        checksum = self.get_chksum(final_pak)
        packet = packet[:16] + struct.pack('H', checksum) + packet[18:] + self.data
        return packet


# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done
SERVER_POOL = [('192.168.1.147', 80), ('192.168.1.143',80)]

# dumb python socket echo server, long tcp connection
# $ ~  while  python server.py
# SERVER_POOL = [('localhost', 6666)]


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
        print('recving packets: %-20s ==> %-20s, data: %s' % (sock.getpeername(), sock.getsockname(), [data]))
        # data can be modified before forwarding to server
        # lots of add-on features can be added here
        remote_socket = self.flow_table[sock]
        # TODO: Here we need to manipulate the data to have the IP of the client, but data includes only HTTP
        dst = sock.getpeername()[0]
        pak = TCPPacket(
            sock.getsockname()[0],
            sock.getsockname()[1],
            sock.getpeername()[0],
            sock.getpeername()[1],
            0b000011000,  # PUSH, ACK
            data
        )
        #print(pak.build())
        remote_socket.send(data)
        #new_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        #new_sock.sendto(pak.build(), remote_socket.getpeername())
        print('sending packets: %-20s ==> %-20s, data: %s' % (remote_socket.getsockname(), remote_socket.getpeername(), [data]))

    def on_close(self, sock):
        print('client %s has disconnected' % (sock.getpeername(),))
        print('='*41+'flow end'+'='*40)

        ss_socket = self.flow_table[sock]

        self.sockets.remove(sock)
        self.sockets.remove(ss_socket)

        new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        new_sock.bind(('172.20.0.2', 50630))
        # new_sock.bind(('192.168.1.142', 50630))
        new_sock.connect(('172.20.0.4', 80))
        # new_sock.connect(('192.168.1.143', 80))
        print(f'New {new_sock.getsockname()}')

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
