#!/bin/sh
set -e

gunicorn --bind 127.0.0.1:8001 --workers 2 --timeout 120 \
    --access-logfile - --error-logfile - \
    --access-logformat '%(h)s "%(r)s" %(s)s %(b)s %(L)ss "%(f)s" "%(a)s"' \
    app:app &
exec nginx -g 'daemon off;'
