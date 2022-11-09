import socket, array

HOST = "0.0.0.0"
PORT = 80


def send_fds(sock, msg, fds):
    return sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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

            client_unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_unix.connect("/tmp/test")
            #client_unix.send(b"Client 1: hi\n")
            #client_unix.send_fds(client, data, [client.fileno()])
            send_fds(client_unix, b"AAAAA", [client.fileno()])
            print("Sent FD")

            client.sendall(data)
	   
            
