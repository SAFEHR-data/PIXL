#
# Dockerfile for vsftpd
#

FROM alpine:3.19.1

RUN set -xe \
    && apk add -U vsftpd \
    && rm -rf /var/cache/apk/*

ADD vsftpd.conf vsftpd.email_passwords vsftpd.banner /etc/vsftpd/
RUN ln -s /etc/vsftpd/vsftpd.email_passwords /etc/vsftpd.email_passwords

RUN install -d -m u+wx,u-r,g+rwxs,o-rwx -o ftp -g root /var/lib/ftp/incoming
RUN ln -sf /proc/1/fd/1 /var/log/vsftpd.log
VOLUME /var/lib/ftp/incoming
WORKDIR /var/lib/ftp

EXPOSE 21

COPY run-vsftpd.sh  /usr/sbin
CMD ["/usr/sbin/run-vsftpd.sh"]