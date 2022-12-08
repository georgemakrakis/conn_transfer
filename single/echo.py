import socket, array, time, os
import subprocess

# HOST = "0.0.0.0"
HOST = "172.20.0.3"
PORT = 80


def send_fds(sock, msg, fds):
    return sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    client, addr = s.accept()
    #print("Client FD: ",client.fileno())
    with client:
        print(f"Connected by {addr}")
        while True:
            data = client.recv(1024)
            if not data:
                break

            # NOTE: Here we had the os.write for the socket descriptor

            # time.sleep(10)

            client_unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_unix.connect("/tmp/test")
            #client_unix.send(b"Client 1: hi\n")
            #client_unix.send_fds(client, data, [client.fileno()])
            send_fds(client_unix, b"AAAAA", [client.fileno()])
            print("Sent FD")

            cmd_list = ["sshpass", "-p", "123456", "scp",
                        "-o", "StrictHostKeyChecking=no", "dump.dat", "dump_inq.dat", "dump_outq.dat", "root@172.20.0.4:/root/single"]                    

            subprocess.call(cmd_list)
            print("Copied dumped files...")

            # TODO: maybe need to wait here for a bit?

            mig_data = "migrated"
            os.write(client.fileno(), mig_data.encode())

            client.sendall(data)

            time.sleep(10)
            # client.close()
            # s.close()
	   
            
