FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update

RUN apt install software-properties-common -y

# Needed for criu 3.6 but too many depedencies break things
#RUN apt install python python-ipaddr python-protobuf -y

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update
RUN apt install curl nano make wget ssh lynx iproute2 net-tools sshpass python3.6 python3-pip python3.6-distutils -y
RUN apt update

# To dump the whole process
RUN add-apt-repository ppa:criu/ppa
RUN apt update --fix-missing
RUN apt install criu -y

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1
RUN update-alternatives --config python3

# RUN rm /usr/bin/python
RUN ln -s /usr/bin/python3 /usr/bin/python 

RUN pip3 install virtualenv
RUN pip3 install flask
RUN pip3 install Flask-Limiter

# To dump the whole process
#RUN wget -O 'criu_3.6-2_amd64.deb' "https://launchpad.net/ubuntu/+archive/primary/+files/criu_3.6-2_amd64.deb"
#RUN dpkg -i criu_3.6-2_amd64.deb

RUN echo 'root:123456' | chpasswd

RUN adduser --disabled-password --gecos '' www
#RUN RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN wget https://archive.apache.org/dist/httpd/httpd-2.0.39.tar.gz
RUN tar -xvf httpd-2.0.39.tar.gz
RUN cd httpd-2.0.39/ && ./configure --prefix=/usr/local/apache2 && make -j2 && make install
COPY httpd.conf /usr/local/apache2/conf/httpd.conf

RUN /usr/local/apache2/bin/apachectl start

WORKDIR /root
COPY server2_counter.py /root/server2_counter.py
COPY server1_HTTP.py /root/server1_HTTP.py


COPY sshd_config /etc/ssh/sshd_config
COPY migrate-auto.sh /root/migrate-auto.sh

RUN mkdir /root/img-dir

# NOTE: We have to revert some of these routes to connect to internet,
# but the NGINX tutorial has a way to forward internet traffic through the proxy
COPY transparency_cmds_server.sh /root/transparency_cmds_server.sh


EXPOSE 8080