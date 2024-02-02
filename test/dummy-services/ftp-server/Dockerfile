#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
FROM delfer/alpine-ftp-server

COPY /dummy-services/ftp-server/ssl/ /etc/ssl/private/

SHELL ["/bin/sh", "-c"]
RUN echo $'# Attempting to enable FTPS.\n\
ssl_enable=YES\n\
ssl_sslv2=YES\n\
ssl_sslv3=YES\n\
implicit_ssl=YES\n\
require_ssl_reuse=NO\n\
xferlog_std_format=YES\n\
log_ftp_protocol=YES\n\
vsftpd_log_file=/var/log/vsftpd.log\n\
syslog_enable=NO' >> /etc/vsftpd/vsftpd.conf
