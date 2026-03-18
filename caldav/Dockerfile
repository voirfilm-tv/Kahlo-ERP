FROM python:3.12-alpine

RUN apk add --no-cache apache2-utils su-exec && \
    pip install --no-cache-dir radicale==3.3.3 bcrypt passlib[bcrypt]

RUN adduser -D radicale && mkdir -p /data/collections && chown -R radicale:radicale /data

COPY radicale.conf /etc/radicale/config
COPY radicale-init.sh /etc/radicale/init.sh
RUN chmod +x /etc/radicale/init.sh

EXPOSE 5232

ENTRYPOINT ["/bin/sh", "/etc/radicale/init.sh"]
