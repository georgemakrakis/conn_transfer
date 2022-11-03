FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update

RUN apt install nano nginx -y

RUN service nginx start

#WORKDIR /root
#COPY server2_counter.py /root/server2_counter.py

COPY load-balancer.conf /etc/nginx/conf.d/load-balancer.conf
RUN rm /etc/nginx/sites-enabled/default

RUN service nginx restart

WORKDIR /root

