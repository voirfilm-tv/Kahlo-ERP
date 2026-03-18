# Fallback Dockerfile for Radicale CalDAV
# Use this if tomsquest/docker-radicale is no longer available on Docker Hub.
# In docker-compose.yml, replace:
#   image: tomsquest/docker-radicale:3.3.3.1
# with:
#   build: ./caldav

FROM python:3.12-alpine

RUN apk add --no-cache apache2-utils su-exec && \
    pip install --no-cache-dir radicale==3.3.3 bcrypt passlib[bcrypt]

RUN adduser -D radicale && mkdir -p /data/collections && chown -R radicale:radicale /data

EXPOSE 5232

# Entrypoint (init.sh) handles user switching via su-exec
CMD ["python", "-m", "radicale", "--config", "/etc/radicale/config"]
