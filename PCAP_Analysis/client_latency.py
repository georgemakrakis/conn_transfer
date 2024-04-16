from scapy.all import *
import datetime, os

count = 0
total = 0
start = 0.0
end = 0.0
lst = []

pcap_AVGDelay = []

exp = 30

# Measure the Inter-Arrival time of packets
directory = f"/mnt/c/Users/georg/source/repos/conn_transfer/tcpdump/client_1/migration/{exp}"
# directory = f"/mnt/c/Users/georg/source/repos/conn_transfer/tcpdump/client_1/migration/{exp}_2"
# directory = f"/mnt/c/Users/georg/source/repos/conn_transfer/tcpdump/client_1/no_migration/{exp}"

for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    if os.path.isfile(f):

        packet_port_startTime = []
        packet_port_latency = []

        # Performs filtering similar to the following in Wireshark and gets the delta time:
        # tcp.flags.push == 1 && tcp.flags.ack == 1 && (tcp.srcport == 52626 && tcp.payload contains "AAA") || (tcp.dstport == 52626 && tcp.payload contains "mig")
        for packet in PcapReader(f):
            # if packet.haslayer(TCP) and packet.haslayer(TLS):
            if 'IP' in packet:
                try:
                    # if packet[IP].src == "172.18.0.2" and len(packet) == 102:
                    # if packet[IP].src == "172.18.0.3" and TLS(packet.load).type == 23: # Mesaure only the Application Data exchanged

                    # First we keep track of when the "request" was sent from the client
                    if packet[IP].src == "172.20.0.100" and packet[TCP].flags == "PA":

                        total += 1
                        
                        packet_port_startTime.append((packet[TCP].sport, packet.time))

                        # if count == 0:
                        #     start = packet.time
                        #     count += 1
                        # elif count == 1:
                        #     end = packet.time            
                        #     count = 0
                        #     # lst.append((end - start)*1000) # time in milliseconds
                        #     lst.append((end - start))

                    if packet[IP].dst == "172.20.0.100" and packet[TCP].flags == "PA":
                        
                        startTime_result = [startTime for (sport, startTime) in packet_port_startTime if sport == packet[TCP].dport]
                        
                        diff = packet.time - startTime_result[0]

                        exists = [index for index, element in enumerate(packet_port_latency) if element[0] == packet[TCP].dport]

                        if not exists:
                            packet_port_latency.append((packet[TCP].dport,diff))
                        elif len(exists) == 1:
                            packet_port_latency[exists[0]] = (packet[TCP].dport, diff)
                        else:
                            print("More that one the same")

            

                        # total += 1                            
                except AttributeError:
                    pass

        # print(packet_port_startTime)
        print(packet_port_latency)

        pcap_AVGDelay.append((f, (sum(n for _, n in packet_port_latency)/len(packet_port_latency))))\
        
        # print(pcap_AVGDelay)
        # os._exit(1)
        

print(f"Directory: {directory}")
print(f"Total packets send from client: {(total)} ({int(total/100)} packets 100 times)")
print(f"Average time packets: {(sum(n for _, n in pcap_AVGDelay)/len(pcap_AVGDelay))}")
