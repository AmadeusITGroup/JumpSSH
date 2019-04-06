FROM alpine:latest

# install base packages
RUN apk --update add openssh sudo curl

# allow root login and tunnel device forwarding
RUN sed -i s/#PermitRootLogin.*/PermitRootLogin\ yes/ /etc/ssh/sshd_config \
  && echo "root:password" | chpasswd \
  && sed -i s/#PermitTunnel.*/PermitTunnel\ yes/ /etc/ssh/sshd_config \
  && sed -i s/AllowTcpForwarding.*/AllowTcpForwarding\ yes/ /etc/ssh/sshd_config \
  && sed -i s/#PermitOpen.*/PermitOpen\ any/ /etc/ssh/sshd_config \
  && rm -rf /tmp/* /var/cache/apk/*

## create individual user accounts
RUN \
  adduser -D -s /bin/ash user1 && \
  echo "user1:password1" | chpasswd && \
  chown -R user1:user1 /home/user1 && \
  adduser -D -s /bin/ash user2 && \
  echo "user2:password2" | chpasswd && \
  chown -R user2:user2 /home/user2

# give sudo permission to user1
RUN echo "user1	 ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/my_sudoers

RUN ssh-keygen -A

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
