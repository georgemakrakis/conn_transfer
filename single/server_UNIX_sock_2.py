from socketserver import UnixStreamServer, StreamRequestHandler, ThreadingMixIn
import os, socket, array


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

print("Opening socket...")
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind("/tmp/test")

server.listen(1)
print("Listening...")

while True:
    client, addr = server.accept()
    #data = client.recv(1024)
    #print(data)
    msg2, fds_arr = recv_fds(client, 5, 3)
    print("FDS: ", fds_arr)