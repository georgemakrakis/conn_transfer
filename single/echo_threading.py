import argparse
import multiprocessing
import random
import socket, array, time, os, logging
import subprocess, fcntl, select
import threading
import uuid

import concurrent.futures

HOST = "172.20.0.3"
PORT = 80

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

logging.basicConfig(filename='server.log', filemode='w', level=logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)

# migration_signal_sent = threading.local()
migration_signal_sent = False

logs_path = ""

def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

class ThreadedServer(object):

    def __init__(self, host=None, port=None, threads=None):
        if host and port and threads:
            self.host = host
            self.port = port
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))

            # Say we can handle N-threads plus the main thread
            self.threads = threads + 1

            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=threads)

            self.lock = threading.Lock()

            self.fds = threading.local() 

            self.last_fd = None

            # self.migration_signal_sent = False
            # self.migration_signal_sent = threading.local()

    def recv_fds(self, sock, msglen, maxfds):
        fds = array.array("i")   # Array of ints
        msg, ancdata, flags, addr = sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
                # Append data, ignoring any truncated integers at the end.
                fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
        return msg, list(fds)

    def send_fds(self, sock, msg, fds):
        try:
            return sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])
        except Exception as e:
            logging.debug(f"SEND FDS: {e}")

    def listen(self):
        # self.sock.listen(100)
        self.sock.listen()
        logging.info("Listening on port %s ..." % PORT)
        
        self.fds.value = []
        # self.migration_signal_sent.value = False
        # global migration_signal_sent
        # migration_signal_sent.value = False

        while True:
            logging.debug(f"{threading.current_thread().name}  Active Thread Count: {threading.active_count()}")
            # logging.debug(f"{threading.current_thread().name}  Active Thread Count 1: {self.executor._work_queue.qsize()}")
            conn, addr = self.sock.accept()
            conn.settimeout(100)

            # print(f"Connected by {addr}")

            # # TODO each one of these ports should be read from a config file along with the LB IP and current server IP.
            # if (self.migration_signal_sent) and (conn.getpeername()[1] == 4000):
            # # if self.migration_signal_sent:
            #     # NOTE: could that be with thread?
            #     # new_thread = threading.Thread(target = self.listenToClient_mig, args = (conn,addr))
            #     # new_thread.start()

            #     logging.debug(f"{threading.current_thread().name} ++++++++++ {self.fds.value}")

            #     self.listenToClient_mig(conn, addr, self.fds.value)


            #     # TODO: Here we should release the migration_signal_sent 
            #     # but we also need to kill the rest of threads 
            #     # so the next contidion will not be triggered again.
            #     self.migration_signal_sent = False

            #     continue

            # TODO: Should if not accepting more, be putting the tasks in a queue and execute them later?
            # if threading.active_count() <= self.threads:
            # new_thread = threading.Thread(target = self.listenToClient, args = (conn,addr, self.fds.value, self.migration_signal_sent.value))
            new_thread = threading.Thread(target = self.listenToClient, args = (conn,addr, self.fds.value))
            new_thread.start()

            # NOTE: That is an arbitrary condition for simple testing, 
            # can be somethine else like the volume of traffic that triggers the migration
            # elif (threading.active_count() > self.threads) and (not self.migration_signal_sent): # Now we send the migration condition signal

            #     logging.debug(f"{threading.current_thread().name}  Active Thread Count: {threading.active_count()}, reached capacity, time to migrate")
            #     migration_signal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #     migration_signal_sock.connect(("172.20.0.2", 80))
            #     migration_signal_sock.send("threads_full\n".encode())

            #     migration_signal_sock.close()
            #     self.migration_signal_sent = True
            #     continue
            #     # break


            # self.executor.submit(self.listenToClient, conn, addr)

    def handle_data(self, conn, data, addr, fds):
    # def handle_data(self, conn, data, addr, fds, migration_signal_sent):
        global migration_signal_sent

        # We lock the access to the global resource and to the if statement
        # so other threads will not be able to access it and send duplicate messages to the LB
        with self.lock:
            # if (threading.active_count() > self.threads) and (not migration_signal_sent) and (data.find(b"\n") != -1): # Now we send the migration condition signal
            # if (data.find(b"BBB\n") != -1) and (not migration_signal_sent) and (data.find(b"\n") != -1): # Now we send the migration condition signal
            if (data.find(b"BBB\n") != -1) and (data.find(b"\n") != -1): # Now we send the migration condition signal
                
                try:
                    socket_id = data.decode().split("$",2)[1]
                except IndexError as er:
                    logging.error(er)

                fds.append((socket_id, conn.fileno()))

                logging.debug(f"{threading.current_thread().name}  WILL SEND: {data}")
                conn.sendall(data)

                # TODO: Do we need to pause all the other threads from execution? 
                # Most probably we can't, see: https://stackoverflow.com/a/13399592/7189378
                # We can attempt to make this hack with signals and flags but we might have 
                # a sleep and performance issue that we want to measure.
                # https://alibaba-cloud.medium.com/detailed-explanation-and-examples-of-the-suspension-recovery-and-exit-of-python-threads-d4c077509461 

                logging.debug(f"{threading.current_thread().name}  Active Thread Count: {threading.active_count()}, reached capacity, time to migrate")
                migration_signal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                migration_signal_sock.connect(("172.20.0.2", 80))
                migration_signal_sock.send(f"threads_full${socket_id}$\n".encode())

                migration_signal_sock.close()
                # self.migration_signal_sent = True
                # migration_signal_sent = True

                # NOTE: We do not return here since this action will close the socket as well 
                # while we want it to be in ESTABLISHED state.
                return 2
        
        if (data.find("mig_signal_2".encode()) != -1) and (data.find(b"\n") != -1):
            try:
                # self.lock.acquire()

                try:
                    socket_id = data.decode().split("$",2)[1]
                except IndexError as er:
                    logging.error(er)

                fds.append((socket_id, conn.fileno()))
                logging.debug(f"{threading.current_thread().name} ******************* FD No: {fds}")

                timeStarted = time.time()

                dumped_socket_pref = (int)(data.decode().split("@",2)[1])

                conn.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)
                
                logging.debug("Restoring...")

                path = "/migvolume1/"
                # path = "/root/single/dumped_connections/"

                inq = None
                with open(f"{path}{dumped_socket_pref}_dump_inq.dat", mode="rb") as inq_file:
                    inq = inq_file.read()
                
                if inq == None:
                    logging.debug("INQ NONE")

                if inq == b'':
                    logging.warning("INQ empty, correcting...")
                    inq = b"\x00\x00\x00\x00\x00\x00\x00\x00"

                logging.debug(inq)

                outq = None
                with open(f"{path}{dumped_socket_pref}_dump_outq.dat", mode="rb") as outq_file:
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

                # migration_counter += 1

                logging.debug(f"{threading.current_thread().name}  WILL SEND: {data}")
                conn.sendall(data)

                timeDelta = time.time() - timeStarted

                metrics_logger_restore = setup_logger('metrics_logger_restore', logs_path)
                metrics_logger_restore.info(f'Restore time for {1} connection (parallel): {timeDelta}')

                # Let's remove every file that we restored.
                os.remove(f"{path}{dumped_socket_pref}_dump.dat")
                os.remove(f"{path}{dumped_socket_pref}_dump_inq.dat")
                os.remove(f"{path}{dumped_socket_pref}_dump_outq.dat")

                return 4

                # self.lock.release()

            except Exception as ex:
                # print("Could not use TCP_REPAIR mode")
                logging.error(f"Issue with Socket Restoration {ex}")

            # TODO: These checks for the condition should be something different in the future
            # can be something that comes from and IPC. 
        if (addr[0] == "172.20.0.2") and (data.find("migration".encode()) != -1) and (data.find(b"\n") != -1):

            # print(f"Current FD No: {conn.fileno()}")

            # timeStarted = time.time()

            try:
                socket_id = data.decode().split("$",2)[1]
            except IndexError as er:
                logging.error(er)

            # time.sleep(10)

            # self.lock.acquire()
            dumped_sockets_num = 0


            # NOTE: Dump a random half of the sockets
            # migrated_sockets_fds = random.sample(fds, round(len(fds)/2))

            # Lists with first and second half of connections.
            migrated_sockets_fds_1 = fds [0:round(len(fds)/2)]
            migrated_sockets_fds_2 = fds [round(len(fds)/2):len(fds)]

            # migrated_sockets_fds_1.sort(key = lambda fd: fd[1])
            # migrated_sockets_fds_2.sort(key = lambda fd: fd[1])

            logging.debug(f"HALF SELECTION OF FDs: {migrated_sockets_fds_1}")
            logging.debug(f"OTHER HALF SELECTION OF FDs: {migrated_sockets_fds_2}")

            results = []

            checkpoint_threads = []

            # try:
            #     pool = multiprocessing.Pool()
            #     outputs_async = pool.map_async(connection_checkpoint, migrated_sockets_fds)
            #     results = outputs_async.get()
            # except Exception as e:
            #     logging.error(f"POOL: {e}")
            #     logging.error(f"POOL EXCEPTION: {type(migrated_sockets_fds)}")
            
            # both_halves = [migrated_sockets_fds_1, migrated_sockets_fds_2]
            old_dumped_sockets_num = ""
            for index, migrated_sockets_fds in enumerate([migrated_sockets_fds_1, migrated_sockets_fds_2]):
                timeStarted = time.time()

                dumped_socket_ids = ""
                
                for fd in migrated_sockets_fds:
                    
                    new_checkpoint_thread = threading.Thread(target = self.connection_checkpoint, args = (fd, results))
                    # checkpoint_threads.append(new_checkpoint_thread)
                    new_checkpoint_thread.start()
                    new_checkpoint_thread.join()

               
                if (all(result == 1 for result in results)):
                    
                    # dumped_socket_ids += "$"
                    # for fd in migrated_sockets_fds:
                    #     # The @ is used to identify the file of the dumped socket.
                    #     # +1 because when FD is acessed it increases by one and
                    #     # -4 to identify the socket.
                    #     dumped_socket_ids += f"{fd[0]}$$@{fd[1] + 1 - 4}@"

                    # dumped_socket_ids += "$"

                    dumped_socket_ids += "$"
                    dumped_socket_ids += "$$".join(map(lambda fd: fd[0], migrated_sockets_fds))
                    dumped_socket_ids += "$"

                    # entries = os.scandir("/migvolume1/")
                    # prefixes = []
                    # for entry in entries:
                    #     pref = (entry.name.split('_')[0])
                    #     if pref not in prefixes:
                    #         prefixes.append(pref)

                    dumped_socket_ids += "@"
                    dumped_socket_ids += "@@".join(map(lambda fd: str(fd[1] + 1 - 4), migrated_sockets_fds))
                    # dumped_socket_ids += "@@".join(map(lambda pref: pref, prefixes))
                    dumped_socket_ids += "@"
                    

                else:
                    logging.debug(f"{threading.current_thread().name} Not all sockets dumped, investigate")
                    os._exit(-1)
                
                # Add also the socket_id for the migration signal socket
                # dumped_socket_ids += f"${socket_id}$"

                # self.lock.release()
                logging.debug(f"{threading.current_thread().name} Sent FDs")

                # logging.debug(f"{threading.current_thread().name}  Active Thread Count 3: {self.executor._work_queue.qsize()}")

                # TODO: here also we need to have DYNAMICALLY the server IP that the files
                # will be sent to.
                scp_cmd_list = ["sshpass", "-p", "123456", "scp",
                        "-o", "StrictHostKeyChecking=no",
                            "-r", "/root/single/dumped_connections",
                        "root@172.20.0.4:/root/single"]

                rsync_cmd_list = ["/bin/bash","/root/single/rsync.sh", "172.20.0.4"]

                # subprocess.call(rsync_cmd_list)

                logging.info("Copied dumped files...")
                # print(f"FD No after: {conn.fileno()}")

                # TODO: What if we do not send data back but we just stop the from beeing sent
                # by blocking them using IPTables? (maybe do not block ACK since we might have duplicate messages)
                data = data.decode().replace("\n", "")
                if index == 0:
                    data = data.replace(f"${socket_id}$", dumped_socket_ids)
                else:
                    data = data.replace(f"{socket_id}", dumped_socket_ids)
                    # data = data.replace(f"@{old_dumped_sockets_num}@", str(dumped_sockets_num))

                # data = f"{data}@{dumped_sockets_num}@\n".encode()
                data = f"{data}\n".encode()
                logging.debug(f"{threading.current_thread().name}  WILL SEND: {data}")
                conn.sendall(data)

                socket_id = dumped_socket_ids
                old_dumped_sockets_num = dumped_sockets_num
                # socket_id = socket_id.replace("$", "")

                # Remove the migrated connections.
                for mig_fd in migrated_sockets_fds:
                    if mig_fd in fds:
                        fds.remove(mig_fd)
                

                timeDelta = time.time() - timeStarted

                metrics_logger_checkpoint = setup_logger('metrics_logger_checkpoint', logs_path)
                metrics_logger_checkpoint.info(f'Checkpoint time for {len(migrated_sockets_fds)} connections (parallel): {timeDelta}')
            
            # with self.lock:
            #     migration_signal_sent = False

            return 3

        

        # if data.find(b"\r\n\r\n") != -1 :
        if data.find(b"\n") != -1 :

            try:
                socket_id = data.decode().split("$",2)[1]
            except IndexError as er:
                logging.error(er)

            fds.append((socket_id, conn.fileno()))

            conn.sendall(data)
            return 1

    def connection_checkpoint(self, fd, results):
    # def connection_checkpoint(socket_id, fd):
        try:   
            # if fd[1] != conn.fileno(): # We do not want the current socket to be migrated.
            logging.debug(f"{threading.current_thread().name} DUMPING FD No: {fd[1]}")
            client_unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)    
            client_unix.connect("/tmp/test")
            # dummy_thread = ThreadedServer()
            self.send_fds(client_unix, b"AAAAA", [fd[1]])
            client_unix.close()

            to_close = socket.fromfd(fd[1]-1, socket.AF_INET, socket.SOCK_STREAM)
            to_close.close()

            results.append(1)

            # return 1
        except Exception as e:
            logging.error(f"Connection_Checkpoint {e}")
            results.append(-1)
            # return -1
        
        return

    def listenToClient(self, conn, addr, fds):
        # global migration_signal_sent
        # migration_signal_sent.value = False
        logging.info("waiting to recv")

        # We remove the duplicate FDs. We do not need "while" instead of "if" here 
        # since FDs cannot be reused per https://man7.org/linux/man-pages/man2/close.2.html
        # if conn.fileno() in fds: 
        #     fds.remove(conn.fileno())

        # fds.append(conn.fileno())
        # fds.value = conn.fileno()

        logging.debug(f"{threading.current_thread().name} +++++++++++++++++++ FD No: {fds}")

        data = bytes()
        
        # We never return from the loop to keep the connection alive
        # (this is what we need for our first experiments)
        while True:
            try:
                # Try to receive some data
                data_recv = conn.recv(16)
                data += data_recv
                # logging.debug(f"{threading.current_thread().name}  Data so far.. {data} with len {len(data)}")
                if not data_recv:
                    logging.warning("NO DATA RECV")
                    break

                handle_data_status = self.handle_data(conn, data, addr, fds)

                if handle_data_status == 1:
                    logging.debug(f"{threading.current_thread().name}  WILL SEND: {data}")
                    data = bytes()
                elif handle_data_status == 2:
                    logging.info("Migration signal sent")
                elif handle_data_status == 3:
                    logging.info("Dumping happens")
                    # os._exit(1)
                elif handle_data_status == 4:
                    logging.info("Restoration happens")


            except OSError as ex:
                logging.error(f"Exception {ex} with {str(ex)}")
                break
            except Exception as ex:
                logging.error(f"Exception {ex}")
                break        

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", "--ip", dest = "ip", help = "Use a defined IP")
    parser.add_argument("-logsPath", "--logsPath", dest = "logs_path", help = "Define a path for logs storage")
    options = parser.parse_args()

    return options

def main():
    global logs_path

    options = get_args()
    host = options.ip
    logs_path = options.logs_path
    
    threads = 4
    ThreadedServer(host=host, port=PORT, threads=threads).listen()


if __name__ == "__main__":
    main()