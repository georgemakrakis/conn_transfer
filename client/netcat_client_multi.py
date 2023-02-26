import subprocess, time
import threading, socket
import nclib

HOST = "172.20.0.2"
PORT = 80

def simple_socks_send():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    # print("sending 1st")
    s.send("$AAA$\n".encode())
    print(s.recv(1024))

    time.sleep(30)

    # print("sending 2nd")

    # s.send("$AAA$\n".encode())
    # print(s.recv(1024))

    # time.sleep(10)

def netcat_send():
    echo_cmd_list = ["echo", "-n", "'AAA'"]
    nc_cmd_list = ["nc", str(HOST), str(PORT), "-"]

    # echo_out = subprocess.Popen(echo_cmd_list, stdout=subprocess.PIPE)

    # subprocess.run(nc_cmd_list, stdin=echo_out.stdout)
    nc_proc = subprocess.Popen(nc_cmd_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)    # nc_proc.stdin.write("AAA\n".encode())
    nc_proc.communicate(input="AAA\n".encode())
    # nc_proc.stdin.close()

    time.sleep(30)

    # # Running it again

    # return

def nclib_send():
    nc = nclib.Netcat(connect=(HOST, PORT))

    # receive and deserialize a value
    value = "AAA\n"

    # serialize and send the result value
    nc.send(value.encode())

    data = nc.recv().decode()
    print(data)

    time.sleep(30)
    # nc_proc.communicate(input="AAA\n".encode())
    # time.sleep(10)

    # return

def main():
    for i in range(6):

        # new_thread = threading.Thread(target = nclib_send, args = ())
        # new_thread = threading.Thread(target = netcat_send, args = ())
        new_thread = threading.Thread(target = simple_socks_send, args = ())
        new_thread.start()

    return

if __name__ == '__main__':
    main()