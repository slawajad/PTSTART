FROM postgres:15

ARG DB_REPL_USER
ARG DB_HOST

RUN echo "#!/bin/bash" > /usr/local/bin/init.sh && \
    echo "rm -rf /var/lib/postgresql/data/*" >> /usr/local/bin/init.sh 
RUN echo "until pg_basebackup -h ${DB_HOST} -D /var/lib/postgresql/data -U ${DB_REPL_USER} -vP -w; do" >> /usr/local/bin/init.sh && \
    echo "echo 'Replica not ready, trying again...'" >> /usr/local/bin/init.sh && \
    echo "sleep 1" >> /usr/local/bin/init.sh && \
    echo "done" >> /usr/local/bin/init.sh && \
    echo "echo 'Backup done, starting replica...'" >> /usr/local/bin/init.sh && \
    echo "chown -R postgres:postgres /var/lib/postgresql/data" >> /usr/local/bin/init.sh && \
    echo "chmod 700 /var/lib/postgresql/data" >> /usr/local/bin/init.sh && \
    echo "su - postgres -c '/usr/lib/postgresql/15/bin/postgres -D /var/lib/postgresql/data'" >> /usr/local/bin/init.sh

RUN chmod +x /usr/local/bin/init.sh

CMD ["/usr/local/bin/init.sh"]