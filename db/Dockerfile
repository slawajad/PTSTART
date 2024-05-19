FROM postgres:15

ARG DB_REPL_USER
ARG DB_REPL_PASSWORD
ARG DB_DATABASE

RUN apt update && apt install sed
COPY db/init.sql .

RUN mkdir -p /var/lib/postgressql/data && chown postgres:postgres -R /var/lib/postgressql/data

RUN sed -i 's/REPLUSER/'"$DB_REPL_USER"'/g' /init.sql
RUN sed -i 's/REPLPASSWORD/'"$DB_REPL_PASSWORD"'/g' /init.sql
RUN sed -i 's/tempDATABASE/'"$DB_DATABASE"'/g' /init.sql

RUN mv /init.sql /docker-entrypoint-initdb.d/init.sql

RUN echo "listen_addresses = '*'" >> postgresql.conf
RUN echo "host all all all password" >> pg_hba.conf
RUN echo "host replication ${DB_REPL_USER} all scram-sha-256" >> pg_hba.conf
RUN echo "CREATE USER ${DB_REPL_USER} WITH REPLICATION ENCRYPTED PASSWORD '${DB_REPL_PASSWORD}';" >> /docker-entrypoint-initdb.d/init.sql && \
    echo "SELECT pg_create_physical_replication_slot('replication_slot');" >> /docker-entrypoint-initdb.d/init.sql

RUN echo "wal_level=replica" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "hot_standby=on" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "max_wal_senders=10" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "max_replication_slots=10" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "hot_standby_feedback=on" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "log_replication_commands=on" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "log_min_messages=NOTICE" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "log_min_duration_statement=100" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "log_min_error_statement=ERROR" >> /usr/share/postgresql/postgresql.conf.sample

RUN mkdir -p /oracle/pg_data/archive && \
    chown -R postgres:postgres /oracle/pg_data

EXPOSE 5432
