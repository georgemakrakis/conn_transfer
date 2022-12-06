FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update

RUN apt install nano nginx -y

RUN service nginx start

RUN apt update
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update
RUN apt install python3.6 python3-pip python3.6-distutils iptables
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1
RUN update-alternatives --config python3

# RUN rm /usr/bin/python
RUN ln -s /usr/bin/python3 /usr/bin/python 

#WORKDIR /root
#COPY server2_counter.py /root/server2_counter.py

COPY load-balancer.conf /etc/nginx/conf.d/load-balancer.conf
RUN rm /etc/nginx/sites-enabled/default

RUN service nginx restart

COPY python_load_balancer.py /root/python_load_balancer.py

WORKDIR /root

