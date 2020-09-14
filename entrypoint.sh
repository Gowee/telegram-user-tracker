#!/bin/sh
# entrypoint for Docker
set -e
if [ -z "$SESSION_NAME" ]; then
    mkdir -p /app/session
    export SESSION_NAME="/app/session/anon.session"
fi
exec python -m telegram_user_tracker
