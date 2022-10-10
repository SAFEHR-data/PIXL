FROM postgres:14-bullseye

# OS setup
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

COPY ./postgres/postgres.conf /etc/postgresql/postgresql.conf
RUN chmod a+r /etc/postgresql/postgresql.conf

COPY ./postgres/pixl-db_init.sh /docker-entrypoint-initdb.d/pixl-db_init.sh
RUN chmod +x /docker-entrypoint-initdb.d/pixl-db_init.sh