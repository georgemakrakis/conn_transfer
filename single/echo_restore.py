import os, socket, array, time

HOST = "0.0.0.0"
PORT = 80

TCP_REPAIR          = 19
TCP_REPAIR_QUEUE    = 20
TCP_QUEUE_SEQ       = 21
TCP_REPAIR_OPTIONS  = 22
TCPOPT_MSS = 2
TCPOPT_WINDOW = 3
TCPOPT_TIMESTAMP = 8
TCPOPT_SACK_PERM = 4

TCP_RECV_QUEUE = 1
TCP_SEND_QUEUE = 2

def recv_fds(sock, msglen, maxfds):
    fds = array.array("i")   # Array of ints
    msg, ancdata, flags, addr = sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
            # Append data, ignoring any truncated integers at the end.
            fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
    return msg, list(fds)

if os.path.exists("/tmp/test"):
    os.remove("/tmp/test")

print("Opening Unix socket...")
unix_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
unix_server.bind("/tmp/test")

unix_server.listen(1)
print("Unix Socket Listening...")

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print("Listening on port %s ..." % PORT)

conn, addr = server_socket.accept()
if addr[1] == 50630:
    try:
        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)

        # print(f"New SEQ num: {conn.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)}")

        # conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, TCP_SEND_QUEUE)
        # seq = struct.pack('=L', int(conn[src].seq))
        # conn.setsockopt(socket.SOL_TCP, TCP_QUEUE_SEQ, seq)

        # conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, TCP_RECV_QUEUE)
        # ack = struct.pack('=L', int(conn[dst].seq))
        # conn.setsockopt(socket.SOL_TCP, TCP_QUEUE_SEQ, ack)

        # conn.bind((conn[src].addr, conn[src].port))
        # conn.connect((conn[dst].addr, conn[dst].port))

        # opt = ''
        # opt += struct.pack('=LHH', TCPOPT_WINDOW,
        #                     int(conn[src].wscale), int(conn[dst].wscale))
        # opt += struct.pack('=LL', TCPOPT_MSS, int(conn[src].mss))

        # conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_OPTIONS, opt)

        # conn.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

    except Exception as ex:
        print("Could not turn on TCP_REPAIR mode")
        
    conn.close()
    print("closed")

unix_client, unix_addr = unix_server.accept()
msg2, fds_arr = recv_fds(unix_client, 5, 3)
print("FDS: ", fds_arr[0])

# we use a client socket to send stuf back to the LB as PoC but it definetely does not work
#lient_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#print(f"Inheritable: {os.get_inheritable(fds_arr[0])}")
#os.set_inheritable(fds_arr[0], 1)

client_sock_fd = socket.fromfd(fds_arr[0], socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
print(type(client_sock_fd))
client_sock_fd.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
#client_sock.bind(("192.168.1.142", 55418))

print("Mig socket data")
print(client_sock_fd.recv(4096))

#client_sock = socket.socket(_sock=client_sock_fd)
response = 'HTTP/1.0 200 OK\n\nHello World, SERVER 2'
time.sleep(10)
client_sock_fd.sendall(response.encode())

#while True:
#    client, addr = server_socket.accept()
#    with client:
#        print(f"Connected by {addr}")   
#        data = client.recv(1024)
#        print(data)
#        msg2, fds_arr = recv_fds(unix_client, 5, 3)
#        print("FDS: ", fds_arr)
#
#        data = client.recv(1024).decode()
#        if not data:
#            break
#
#        response = 'HTTP/1.0 200 OK\n\nHello World, SERVER 1'
#        client.sendall(response.encode())