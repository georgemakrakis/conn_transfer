import socket, array, time, os
import subprocess

# HOST = "0.0.0.0"
HOST = "172.20.0.3"
PORT = 80

TCP_REPAIR          = 19
TCP_REPAIR_QUEUE    = 20

def recv_fds(sock, msglen, maxfds):
    fds = array.array("i")   # Array of ints
    msg, ancdata, flags, addr = sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
            # Append data, ignoring any truncated integers at the end.
            fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
    return msg, list(fds)

def send_fds(sock, msg, fds):
    return sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print("Listening on port %s ..." % PORT)
    
    while True:
        conn, addr = server_socket.accept()
        with conn:
            print(f"Connected by {addr}")
       
            data = conn.recv(1024)
            if not data:
                break

            if addr[1] == 50630:
                try:
                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)

                    inq = None
                    with open("dump_inq.dat", mode="rb") as inq_file:
                        inq = inq_file.read()

                    print(inq)

                    outq = None
                    with open("dump_outq.dat", mode="rb") as outq_file:
                        outq = outq_file.read()

                    print(outq)

                    # print(f"New SEQ num: {conn.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)}")

                    # conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, outq)
            
                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, inq)
            

                    # Let's proceed with sending the new data
                    conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 0)

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
                #cmd_list = ["sshpass", "-p", "123456", "scp",
                #            "-o", "StrictHostKeyChecking=no", 
                #            "dump.dat", "dump_inq.dat", "dump_outq.dat", 
                #            "root@172.20.0.4:/root/single"]                    

                #subprocess.call(cmd_list)
                print("Copied dumped files...")

                # TODO: maybe need to wait here for a bit?

                # mig_data = "migrated"
                # os.write(client.fileno(), mig_data.encode())
           
            conn.sendall(data)

            # time.sleep(10)
            
            # client.close()
            # s.close()
