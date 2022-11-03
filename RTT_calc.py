from scapy.all import *
import datetime

count = 0
total = 0
start = 0.0
end = 0.0
lst = []

scapy.all.load_layer("http")

# Measure the Inter-Arrival time of packets

for packet in PcapReader(sys.argv[1]):
    if packet.haslayer(TCP) and (packet.haslayer(HTTPRequest) or packet.haslayer(HTTPResponse)):
    # if 'IP' in packet:
        if packet[IP].src == "172.20.0.5" and packet[IP].dst == "172.20.0.2":
            if count == 0:
                start = packet.time
                count += 1
        if packet[IP].src == "172.20.0.2" and packet[IP].dst == "172.20.0.5":
            if count == 1:
                end = packet.time            
                count = 0
                # lst.append((end - start)*1000) # time in milliseconds
                # We can put the whole list in a file at the end or...
                lst.append((end - start))

                # ... we can just print it.
                print((end - start))

        total += 1                            
        
        

print("Total packets: {0}".format(total))