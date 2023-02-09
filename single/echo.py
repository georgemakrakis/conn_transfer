import socket, array, time, os, logging
import subprocess, fcntl, select
import errno

# HOST = "0.0.0.0"
HOST = "172.20.0.3"
PORT = 80

TCP_REPAIR          = 19
TCP_REPAIR_QUEUE    = 20

migration_counter = 0

logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)

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

    migration_counter = 0

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(100)

    print("Listening on port %s ..." % PORT)
    
    while True:
        conn, addr = server_socket.accept()
        # conn.setblocking(False)

        with conn:
            print(f"Connected by {addr}")
            if addr[0] == "172.20.0.2":
                print("waiting to recv")

                # data = conn.recv(1024)
                # if not data:
                #     print("NO DATA RECV")
                #     # break
                #     continue
                
                data = bytes()
                # TODO: Could that be "while True:" ?
                continue_recv = True

                while continue_recv:
                    print("HERE!!!")
                    try:
                        # Try to receive some data
                        data_recv = conn.recv(16)
                        data += data_recv
                        logging.debug(f"Data so far.. {data} with len {len(data)}")
                        if not data_recv:
                            logging.warning("NO DATA RECV")
                            continue_recv = False
                        if data.find(b"\r\n\r\n") != -1 :
                            continue_recv = False
                            migration_counter += 1
                    except Exception as ex:
                        logging.error(f"Exception {ex}")
                        continue_recv = False
                        
                if migration_counter == 6:
                    migration_signal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    migration_signal_sock.connect(("172.20.0.2", 80))
                    migration_signal_sock.send("threads_full".encode())
                    migration_signal_sock.close()
                    migration_counter = 0
                    continue


                # if addr[1] == (50630 + migration_counter):
                if (data.find("mig_signal_2".encode()) != -1):
                    try:
                        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)
                        
                        print("Restoring")

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
                
                print(f"WILL SEND: {data}")
                try:
                    # print(f"SD OK: {(fcntl.fcntl(conn.fileno(), fcntl.F_GETFD) != -1)}")
                    conn.sendall(data)

                    # sent = conn.send(data)
                    # if sent == 0 or sent < len(data):
                    #     print(f"Problem with conn {conn.getsockname()} --> {conn.getpeername()}")

                    conn.close()

                except OSError as ex:
                    print(f"OSError {ex}")

                    print("Trying one more time")
                    conn.sendall(data)
                    # sent = conn.send(data)
                    # if sent == 0 or sent < len(data):
                    #     print(f"Problem with conn {conn.getsockname()} --> {conn.getpeername()}")


                    # print(f"SOCK {conn.getsockname()} --> {conn.getpeername()}")
                # conn.sendall(f"{data.decode()}_{migration_counter}".encode())
            
            else:
                conn.close()

            # time.sleep(10)
            
            # client.close()
            # s.close()