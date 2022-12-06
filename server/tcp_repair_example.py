import socket, struct

TCP_REPAIR = 19


# SERVER_HOST = '127.0.0.1'
SERVER_HOST = '172.23.105.189'
SERVER_PORT = 8080

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(1)
print('Listening on port %s ...' % SERVER_PORT)

while True:
    client_connection, client_address = server_socket.accept()

    # request = client_connection.recv(1024).decode()
    # print(request)

    try:
        client_connection.setsockopt(socket.SOL_TCP, TCP_REPAIR, 1)
    except Exception as ex:
        print("Could not turn on TCP_REPAIR mode")
    
    client_connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # response = 'HTTP/1.1 200 OK Hello World, SERVER 1'
    # client_connection.sendall(response.encode())

    # client_connection.shutdown(1)
    # client_connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    client_connection.close()