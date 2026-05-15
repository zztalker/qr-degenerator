#!/bin/sh
set -e

# Render injects $PORT; locally default to 8000.
export HTTP_PORT="${PORT:-8000}"

envsubst '${HTTP_PORT}' < /app/nginx.conf > /etc/nginx/conf.d/default.conf

# Enable the HTTPS server block only when certs are mounted (local deployment).
if [ -f /etc/letsencrypt/live/ny.zaik.in.rs/fullchain.pem ]; then
    cp /app/nginx-ssl.conf /etc/nginx/conf.d/ssl.conf
fi

gunicorn --bind 127.0.0.1:8001 --workers 2 --timeout 120 \
    --access-logfile - --error-logfile - \
    --access-logformat '%(h)s "%(r)s" %(s)s %(b)s %(L)ss "%(f)s" "%(a)s"' \
    app:app &
exec nginx -g 'daemon off;'
