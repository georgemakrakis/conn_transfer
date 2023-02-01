import socket, array, time, os, logging
import subprocess, fcntl, select
import threading
import uuid

import concurrent.futures

HOST = "172.20.0.3"
PORT = 80

TCP_REPAIR          = 19
TCP_REPAIR_QUEUE    = 20

migration_counter = 0

logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)

class ThreadedServer(object):
    def __init__(self, host, port, threads):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        # Say we can handle N-threads plus the main thread
        self.threads = threads + 1

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=threads)

        self.lock = threading.Lock()

        self.fds_uuids = dict()

        self.migration_signal_sent = False

    def recv_fds(self, sock, msglen, maxfds):
        fds = array.array("i")   # Array of ints
        msg, ancdata, flags, addr = sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
                # Append data, ignoring any truncated integers at the end.
                fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
        return msg, list(fds)

    def send_fds(self, sock, msg, fds):
        return sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])

    def listen(self):
        self.sock.listen(100)
        logging.info("Listening on port %s ..." % PORT)

        while True:
            logging.debug(f"{threading.current_thread().name}  Active Thread Count: {threading.active_count()}")
            # logging.debug(f"{threading.current_thread().name}  Active Thread Count 1: {self.executor._work_queue.qsize()}")
            conn, addr = self.sock.accept()
            conn.settimeout(100)

            if self.migration_signal_sent:
                # NOTE: could that be with thread?
                # new_thread = threading.Thread(target = self.listenToClient_mig, args = (conn,addr))
                # new_thread.start()

                logging.debug(f"{threading.current_thread().name} {self.fds_uuids}")

                self.listenToClient_mig(conn, addr)

                continue

            # TODO: Should if not accepting more be putting the tasks in a queue and execute them later?
            if threading.active_count() <= self.threads:
                new_thread = threading.Thread(target = self.listenToClient, args = (conn,addr))
                new_thread.start()
            else: # Now we send the migration condition signal
                logging.debug(f"{threading.current_thread().name}  Active Thread Count: {threading.active_count()}, reached capacity, time to migrate")
                migration_signal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                migration_signal_sock.connect(("172.20.0.2", 80))
                migration_signal_sock.send("threads_full".encode())

                migration_signal_sock.close()
                self.migration_signal_sent = True
                continue
                # break


            # self.executor.submit(self.listenToClient, conn, addr)

    def listenToClient(self, conn, addr):
        logging.info("waiting to recv")

        self.fds_uuids[str(uuid.uuid4())] = conn.fileno()

        data = bytes()
        continue_recv = True

        while continue_recv:
            try:
                # Try to receive some data
                data_recv = conn.recv(16)
                data += data_recv
                # logging.debug(f"{threading.current_thread().name}  Data so far.. {data} with len {len(data)}")
                if not data_recv:
                    logging.warning("NO DATA RECV")
                    continue_recv = False
                if data.find(b"\r\n\r\n") != -1 :
                    continue_recv = False                        
            except Exception as ex:
                logging.error(f"Exception {ex}")
                continue_recv = False
                        
        logging.debug(f"{threading.current_thread().name}  WILL SEND: {data}")
        try:
            conn.sendall(data)
            return
        except OSError as ex:
            logging.error(f"Exception {ex} with {str(ex)}")
            return

    def listenToClient_mig(self, conn, addr):
        global migration_counter

        while True:
            # logging.debug(f"Active Thread Count 2: {self.executor._work_queue.qsize()}")
            logging.info(f"Connected by {addr}")
            if addr[0] == "172.20.0.2":
                logging.info("waiting to recv")

                # data = conn.recv(1024)
                # if not data:
                #     logging.warning("NO DATA RECV")
                #     # break
                #     continue

                data = bytes()
                continue_recv = True

                while continue_recv:
                    try:
                        # Try to receive some data
                        data_recv = conn.recv(16)
                        data += data_recv
                        logging.debug(f"{threading.current_thread().name} Data so far.. {data} with len {len(data)}")
                        if not data_recv:
                            logging.warning("NO DATA RECV")
                            continue_recv = False
                        if data.find(b"\r\n\r\n") != -1 :
                            continue_recv = False                        
                    except Exception as ex:
                        logging.error(f"Exception {ex}")
                        continue_recv = False

                # if addr[1] == (50630 + migration_counter):
                if (data.find("mig_signal_2".encode()) != -1):
                    try:
                        # self.lock.acquire()

                        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)
                        
                        logging.debug("Restoring...")

                        inq = None
                        with open("/migvolume1/dump_inq.dat", mode="rb") as inq_file:
                            inq = inq_file.read()
                        
                        if inq == None:
                            logging.debug("INQ NONE")

                        if inq == b'':
                            logging.warning("INQ empty, correcting...")
                            inq = b"\x00\x00\x00\x00\x00\x00\x00\x00"

                        logging.debug(inq)

                        outq = None
                        with open("/migvolume1/dump_outq.dat", mode="rb") as outq_file:
                            outq = outq_file.read()

                        if outq == None:
                            logging.debug("OUTQ NONE")

                        if outq == b'':
                            logging.warning("OUTQ empty, correcting...")
                            outq = b"\x00\x00\x00\x00\x00\x00\x00\x00"

                        logging.debug(outq)

                        # print(f"New SEQ num: {conn.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)}")

                        # conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, outq)
                
                        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR_QUEUE, inq)
                

                        # Let's proceed with sending the new data
                        conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 0)

                        migration_counter += 1

                        # self.lock.release()

                    except Exception as ex:
                        # print("Could not use TCP_REPAIR mode")
                        logging.error(f"Issue with Socket Restoration {ex}")

                # TODO: These checks for the condition should be something different in the future
                # can be something that comes from and IPC. 
                if (addr[0] == "172.20.0.2") and (data.find("migration".encode()) != -1):
                    client_unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client_unix.connect("/tmp/test")

                    # print(f"FD No: {conn.fileno()}")

                    # self.lock.acquire()

                    self.send_fds(client_unix, b"AAAAA", [conn.fileno()])

                    # HERE we should dump all the sockets in a loop
                    
                    # self.lock.release()
                    logging.debug("Sent FD")

                    # logging.debug(f"{threading.current_thread().name}  Active Thread Count 3: {self.executor._work_queue.qsize()}")

                    # NOTE: here also we need to have dynamically the server that the files
                    # will be sent to.
                    #cmd_list = ["sshpass", "-p", "123456", "scp",
                    #            "-o", "StrictHostKeyChecking=no", 
                    #            "dump.dat", "dump_inq.dat", "dump_outq.dat", 
                    #            "root@172.20.0.4:/root/single"]                    

                    #subprocess.call(cmd_list)
                    logging.info("Copied dumped files...")
                    # print(f"FD No after: {conn.fileno()}")

                    # TODO: maybe need to wait here for a bit?

                    # mig_data = "migrated"
                    # os.write(client.fileno(), mig_data.encode())
                
                logging.debug(f"{threading.current_thread().name}  WILL SEND: {data}")
                try:
                    # print(f"SD OK: {(fcntl.fcntl(conn.fileno(), fcntl.F_GETFD) != -1)}")
                    conn.sendall(data)
                    return

                except OSError as ex:
                    logging.error(f"Exception {ex} with {str(ex)}")

                    logging.warning("Trying one more time")
                    conn.sendall(data)
                    return
                # conn.sendall(f"{data.decode()}_{migration_counter}".encode())
            
            else:
                conn.close()
                return

def main():
    threads = 4
    ThreadedServer(HOST,PORT, threads).listen()


if __name__ == "__main__":
    main()