#!/bin/sh

certfile=${CERTFILE:-/certs/server.pem}
keyfile=${KEYFILE:-/certs/server.key}
port=${PORT:-8008}

if [ -f "$certfile" ] && [ -f "$keyfile" ]; then
    gunicorn app:app --bind 0.0.0.0:$port --env FLASK_ENV=production --keyfile $keyfile --certfile $certfile --workers 8 --preload
else
    gunicorn app:app --bind 0.0.0.0:$port --env FLASK_ENV=production --workers 8 --preload
fi