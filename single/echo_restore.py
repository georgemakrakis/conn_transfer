import os, socket, array, time
import subprocess

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

migration_counter = 0

def send_fds(sock, msg, fds):
    return sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])

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

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    # global migration_counter

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print("Listening on port %s ..." % PORT)

    while True:
        conn, addr = server_socket.accept()
        with conn:
            print(f"Connected by {addr}")
        

            data = conn.recv(1024)
            if not data:
                break

            if addr[1] == (50630 + migration_counter):
                try:
                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)

                    iinq = None
                    with open("/migvolume1/dump_inq.dat", mode="rb") as inq_file:
                        inq = inq_file.read()

                    print(inq)

                    outq = None
                    with open("/migvolume1/dump_outq.dat", mode="rb") as outq_file:
                        outq = outq_file.read()

                    print(outq)

                    # print(f"New SEQ num: {conn.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)}")

                    # conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, outq)
            
                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, inq)
            

                    # Let's proceed with sending the new data
                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 0)

                    migration_counter += 1

                except Exception as ex:
                    print("Could not use TCP_REPAIR mode")

            
            # TODO: These checks for the condition should be something different in the future
            # can be something that comes from and IPC. 
            if (addr[0] == "172.20.0.2") and (data.find("migration".encode()) != -1):
                client_unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client_unix.connect("/tmp/test")

                send_fds(client_unix, b"AAAAA", [conn.fileno()])
                print("Sent FD")

                # NOTE: here also we need to have dynamically the server that the files
                # will be sent to.
                # cmd_list = ["sshpass", "-p", "123456", "scp",
                #             "-o", "StrictHostKeyChecking=no", 
                #             "dump.dat", "dump_inq.dat", "dump_outq.dat", 
                #             "root@172.20.0.3:/root/single"]                    

                # subprocess.call(cmd_list)
                print("Copied dumped files...")

                # TODO: maybe need to wait here for a bit?

                # mig_data = "migrated"
                # os.write(client.fileno(), mig_data.encode())
                    
            
            # unix_client, unix_addr = unix_server.accept()
            # msg2, fds_arr = recv_fds(unix_client, 5, 3)
            # print("FDS: ", fds_arr[0])

            response = 'HTTP/1.0 200 OK\n\nHello World, SERVER 2'
            # response = 'migration'
            
            # time.sleep(10)

            # We send it to the new socket FROM THE PROXY and not the one we restored.
            # NOTE: The response should be the sent data, since it an echo server
            # but for now we leave this to verify that the migration works.
            conn.sendall(response.encode())
