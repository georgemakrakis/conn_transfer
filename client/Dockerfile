FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update

RUN apt install software-properties-common -y


RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update
RUN apt install curl iputils-ping tcpdump nano make wget ssh netcat python3.6 python3-pip python3.6-distutils -y

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1
RUN update-alternatives --config python3

# RUN update-alternatives --config python3

RUN ln -s /usr/bin/python3 /usr/bin/python 

RUN pip3 install virtualenv
RUN pip3 install flask
RUN pip3 install nclib

WORKDIR /root
COPY client/client1.py /root/client1.py
COPY client/slowloris/slowloris.py /root/slowloris.py
COPY client/client1_threading.py /root/client1_threading.py

COPY client/netcat_client_multi.py /root/netcat_client_multi.py

COPY load-balancer/run_client.sh /root/run_client.sh

COPY load-balancer/tcpdump_start.sh /root/tcpdump_start.sh
COPY load-balancer/tcpdump_stop.sh /root/tcpdump_stop.sh


# EXPOSE 8080
