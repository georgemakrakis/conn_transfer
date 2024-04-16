import subprocess, time, logging
import threading, socket
import nclib

HOST = "172.20.0.2"
PORT = 80

logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)

def simple_socks_send(data):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send(data.encode())
    data = bytes()

    while True:
        try:
            # Try to receive some data
            # data_recv = s.recv(16)
            data_recv = s.recv(10)
            data += data_recv
            # logging.debug(f"{threading.current_thread().name}  Data so far.. {data} with len {len(data)}")
            if not data_recv:
                logging.debug(f"{threading.current_thread().name} NO DATA RECV")
                break
                
            logging.debug(f"{threading.current_thread().name} {data}")
            
            if (data.find(b"mig_signal_2\n") != -1):
            # if (data.find(b"AAA\n") != -1): # For regular connections
                return
        except OSError as ex:
            logging.debug(f"{threading.current_thread().name} Exception {ex} with {str(ex)}")
            break
        except Exception as ex:
            logging.debug(f"{threading.current_thread().name} Exception {ex}")
            break

    # time.sleep(10)


def netcat_send():
    echo_cmd_list = ["echo", "-n", "'AAA'"]
    nc_cmd_list = ["nc", str(HOST), str(PORT), "-"]

    # echo_out = subprocess.Popen(echo_cmd_list, stdout=subprocess.PIPE)

    # subprocess.run(nc_cmd_list, stdin=echo_out.stdout)
    nc_proc = subprocess.Popen(nc_cmd_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # nc_proc.stdin.write("AAA\n".encode())
    nc_proc.communicate(input="AAA\n".encode())
    # nc_proc.stdin.close()

    time.sleep(10)

    # # Running it again
    # nc_proc.communicate(input="AAA\n".encode())
    # time.sleep(10)

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
    # return

def main():
    runs = 100

    for j in range(runs):
        
        run_LB_cmd_list = ["docker", "exec", "load-balancer", "/bin/bash", "/root/run_LB.sh", "/migvolume1/logs/LB.log"]
        subprocess.run(run_LB_cmd_list)


        # mkdir_cmd_list = ["mkdir", f"./tcpdump/client_1"]
        # subprocess.run(mkdir_cmd_list)
        # run_tcpdump_cmd_list = ["docker", "run", "-d", "--rm", "--net=container:client_1", "-v", "/root/tcpdump:/tcpdump", "--name", "tcpdump_1", "kaazing/tcpdump", "-w", "client_1.pcap"] 
        # subprocess.run(run_tcpdump_cmd_list)

        run_tcpdump_cmd_list = ["sh", "tcpdump_start.sh"] 
        subprocess.run(run_tcpdump_cmd_list)

        # mkdir_cmd_list = ["mkdir", f"./tcpdump/load-balancer"]
        # subprocess.run(mkdir_cmd_list)
        # run_tcpdump_cmd_list = ["docker", "run", "-d", "--rm", "--net=container:load-balancer", "-v", "/root/tcpdump:/tcpdump", "--name", "tcpdump_2", "kaazing/tcpdump", "-w", "load-balancer.pcap"]
        # subprocess.run(run_tcpdump_cmd_list)

        # time.sleep(10)

        # max_threads = 4
        # max_threads = 10
        # max_threads = 50
        max_threads = 100
        # max_threads = 200
        # max_threads = 300
        for i in range(max_threads):

            data = "AAA\n"
            
            if i == (max_threads - 1):
                data = "BBB\n" # The condition that will trigger the migration
            
            # new_thread = threading.Thread(target = nclib_send, args = ())
            # new_thread = threading.Thread(target = netcat_send, args = ())
            new_thread = threading.Thread(target = simple_socks_send, args = (data,))
            new_thread.start()

            # if i == 20 or i == 40 or i == 60 or i == 80:
            # if i == 100 or i == 200 or i == 300:
            #     time.sleep(1)


            # time.sleep(100)

        stop_LB_cmd_list = ["bash", "stop_LB.sh"]
        subprocess.run(stop_LB_cmd_list)

        # mv_pcap_cmd_list = ["mv", "/root/tcpdump/client_1/tcpdump.pcap", f"./tcpdump/client_1/tcpdump_{j}.pcap"]
        # subprocess.run(mv_pcap_cmd_list)

        # mv_pcap_cmd_list = ["mv", "/root/tcpdump/load-balancer/tcpdump.pcap", f"./tcpdump/load-balancer/tcpdump_{j}.pcap"]
        # subprocess.run(mv_pcap_cmd_list)
        
        # stop_tcp_cmd_list = ["docker", "stop", "tcpdump_1"]
        # subprocess.run(stop_tcp_cmd_list)

        # stop_tcp_cmd_list = ["docker", "stop", "tcpdump_2"]
        # subprocess.run(stop_tcp_cmd_list)

        stop_tcpdump_cmd_list = ["sh", "tcpdump_stop.sh"] 
        subprocess.run(stop_tcpdump_cmd_list)

        mv_pcap_cmd_list = ["mv", "/root/tcpdump/client_1.pcap", f"./tcpdump/client_1/tcpdump_{j}.pcap"]
        subprocess.run(mv_pcap_cmd_list)

        time.sleep(90)

    return

if __name__ == '__main__':
    main()
