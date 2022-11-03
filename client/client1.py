import socket
import time
# HOST = "192.168.1.141"
# HOST = "192.168.1.142"

HOST = "172.20.0.2" # LB
# HOST = "172.20.0.3" # Server 1
# HOST = "172.20.0.4" # Server 2
PORT = 80

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #count = 0
    s.connect((HOST, PORT))
    # while True:
    for i in range(1, 1001):
        #count += 1
        #s.sendall(f"hello {count}".encode())
        #data = s.recv(1024)
        #print(f"Received {data!r}")

        # s.send(b"GET / HTTP/1.0\r\nHost:192.168.1.141\r\n\r\n")
        # s.send(b"GET / HTTP/1.1\r\nHost:192.168.1.142\r\n\r\n")

        # s.send(b"GET /counter HTTP/1.1\r\nHost:192.168.1.142\r\n\r\n")
        sent_time = time.time()
        s.send(b"GET /counter HTTP/1.1\r\nHost:172.20.0.2\r\n\r\n")
        # s.send(b"GET /counter HTTP/1.0\r\nHost:192.168.1.141\r\n\r\n")
        response = s.recv(4096)
        receive_time = time.time()
        #print(response.decode())
        print(receive_time-sent_time)

        time.sleep(0.1)

