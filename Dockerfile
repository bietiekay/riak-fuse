FROM debian:jessie

# install open ssh server
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:root' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

RUN apt-get install -y supervisor
RUN touch /var/run/supervisor.sock
RUN chmod 777 /var/run/supervisor.sock

# install supervisor
ADD docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ADD docker/.bash_profile /root/.bash_profile

EXPOSE 22

ADD . /src/riak-fuse

# install mysql client, php5-fpm nginx and git
RUN apt-get install -y pkg-config libtool autoconf build-essential gcc automake make libffi-dev libssl-dev openssl curl apt-transport-https libc6-dev-i386 wget

RUN wget -O /tmp/fuse.tar.gz https://github.com/libfuse/libfuse/releases/download/fuse-2.9.7/fuse-2.9.7.tar.gz
RUN tar xvf /tmp/fuse.tar.gz --directory /tmp
WORKDIR "/tmp/fuse-2.9.7/"

RUN ./configure
RUN make -j8
RUN make install

RUN apt-get install -y python python-pip
RUN pip install fusepy
RUN pip install riak
WORKDIR "/src/riak-fuse"

CMD ["/usr/bin/supervisord"]
