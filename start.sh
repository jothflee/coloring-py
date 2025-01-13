#!/bin/sh

certfile=${CERTFILE:-/certs/server.pem}
keyfile=${KEYFILE:-/certs/server.key}
port=${PORT:-8008}

gunicorn_cmd="gunicorn app:app --bind 0.0.0.0:$port --env BASIC_AUTH_USERNAME=$BASIC_AUTH_USERNAME --env BASIC_AUTH_PASSWORD=$BASIC_AUTH_PASSWORD --env FLASK_ENV=production --env OPENAI_API_KEY=$OPENAI_API_KEY --workers 8 --preload"

if [ -f "$certfile" ] && [ -f "$keyfile" ]; then
    gunicorn_cmd="$gunicorn_cmd --keyfile $keyfile --certfile $certfile"
fi

exec $gunicorn_cmd