import os, socket, array

HOST = "0.0.0.0"
PORT = 80

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
print('Listening on port %s ...' % PORT)

unix_client, unix_addr = unix_server.accept()

while True:
    client, addr = server_socket.accept()
    with client:
        print(f"Connected by {addr}")   
        data = client.recv(1024)
        print(data)
        msg2, fds_arr = recv_fds(unix_client, 5, 3)
        print("FDS: ", fds_arr)

        data = client.recv(1024).decode()
        if not data:
            break
        response = 'HTTP/1.0 200 OK\n\nHello World, SERVER 1'
        client.sendall(response.encode())
    

