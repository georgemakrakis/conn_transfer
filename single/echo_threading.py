import socket, array, time, os
import subprocess, fcntl, select

# HOST = "0.0.0.0"
HOST = "172.20.0.4"
PORT = 80

TCP_REPAIR          = 19
TCP_REPAIR_QUEUE    = 20

migration_counter = 0

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
    # global migration_counter

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(100)

    print("Listening on port %s ..." % PORT)
    
    while True:
        conn, addr = server_socket.accept()

        with conn:
            print(f"Connected by {addr}")
            if addr[0] == "172.20.0.2":
                print("waiting to recv")


                data = conn.recv(1024)
                if not data:
                    print("NO DATA RECV")
                    break

                # if addr[1] == (50630 + migration_counter):
                if (data.find("mig_signal_2".encode()) != -1):
                    try:
                        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)

                        print("Restoring...")

                        inq = None
                        with open("/migvolume1/dump_inq.dat", mode="rb") as inq_file:
                            inq = inq_file.read()
                        
                        if inq == None:
                            print("INQ NONE")

                        if inq == b'':
                            print("INQ empty, correcting...")
                            inq = b"\x00\x00\x00\x00\x00\x00\x00\x00"

                        print(inq)

                        outq = None
                        with open("/migvolume1/dump_outq.dat", mode="rb") as outq_file:
                            outq = outq_file.read()

                        if outq == None:
                            print("OUTQ NONE")

                        if outq == b'':
                            print("OUTQ empty, correcting...")
                            outq = b"\x00\x00\x00\x00\x00\x00\x00\x00"

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

                    # print(f"FD No: {conn.fileno()}")

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
                    # print(f"FD No after: {conn.fileno()}")

                    # TODO: maybe need to wait here for a bit?

                    # mig_data = "migrated"
                    # os.write(client.fileno(), mig_data.encode())

                response = "HTTP/1.1 200 OK\n\nHello World, SERVER 2"
                # print(f"WILL SEND: {response.encode()}")
                # conn.sendall(response.encode())

                print(f"WILL SEND: {data}")

                try:
                    # print(f"SD OK: {(fcntl.fcntl(conn.fileno(), fcntl.F_GETFD) != -1)}")
                    conn.sendall(data)

                except OSError as ex:
                    print(f"OSError {ex}")
                # conn.sendall(f"{data.decode()}_{migration_counter}".encode())

            else:
                conn.close()

            # time.sleep(10)
            
            # client.close()
            # s.close()
