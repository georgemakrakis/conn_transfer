FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update  --fix-missing

# RUN apt install nano nginx -y
# RUN apt update

RUN apt install nano build-essential iproute2 iptables libreadline-dev unzip -y
RUN apt update
RUN apt install lua5.3 liblua5.3-dev -y

WORKDIR /root

# For OpenResty
RUN apt -y install --no-install-recommends wget gnupg ca-certificates
RUN wget -O - https://openresty.org/package/pubkey.gpg | apt-key add -
# RUN echo "deb http://openresty.org/package/ubuntu $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/openresty.list
RUN echo "deb http://openresty.org/package/ubuntu focal main" | tee /etc/apt/sources.list.d/openresty.list
RUN apt update
RUN apt install openresty -y

RUN wget https://luarocks.org/releases/luarocks-3.8.0.tar.gz
RUN tar zxpf luarocks-3.8.0.tar.gz
RUN cd luarocks-3.8.0 && ./configure --with-lua=/usr/ --with-lua-include=/usr/include/lua5.3/ && make -j2 && make install
 
RUN luarocks install lua-resty-reqargs
#RUN luarocks install cliargs
RUN luarocks install luastatic 

#RUN service nginx start
RUN service openresty start

#WORKDIR /root
#COPY server2_counter.py /root/server2_counter.py

RUN mkdir /usr/local/openresty/nginx/sites
COPY load-balancer.conf /usr/local/openresty/nginx/sites/load-balancer.conf
COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY nginx.conf.bak /usr/local/openresty/nginx/conf/nginx.conf.bak
RUN mv /usr/local/openresty/nginx/conf/nginx.conf.default /usr/local/openresty/nginx/conf/nginx.conf.default.bak
COPY rewrite-upstream.lua /usr/local/openresty/nginx/html/rewrite-upstream.lua
COPY rewrite-upstream_2.lua /usr/local/openresty/nginx/html/rewrite-upstream_2.lua

#COPY load-balancer.conf /etc/nginx/conf.d/load-balancer.conf
#RUN rm /etc/nginx/sites-enabled/default

#RUN service nginx restart

COPY transparency_cmds.sh /root/transparency_cmds.sh
#RUN ip rule add fwmark 1 lookup 100
#RUN ip route add local 0.0.0.0/0 dev lo table 100
#RUN iptables -t mangle -A PREROUTING -p tcp -s 172.20.0.0/16 --sport 80 -j MARK --set-xmark 0x1/0xffffffff

RUN echo 'print("hello world!")' > hello.lua

EXPOSE 80

