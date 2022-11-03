import socket
import time
#HOST = "192.168.108.141"
HOST = "192.168.1.142"
PORT = 80

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    count = 0
    s.connect((HOST, PORT))
    while True:
        count += 1
        s.sendall(f"hello {count}".encode())
        data = s.recv(1024)
        print(f"Received {data!r}")
        time.sleep(2)
