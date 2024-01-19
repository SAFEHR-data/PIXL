FROM delfer/alpine-ftp-server

SHELL ["/bin/sh", "-c"]
RUN echo $'# Attempting to enable FTPS.\n\
ssl_enable=YES\n\
ssl_sslv2=YES\n\
ssl_sslv3=YES\n\
implicit_ssl=YES\n\
require_ssl_reuse=NO' >> /etc/vsftpd/vsftpd.conf