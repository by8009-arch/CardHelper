#!/bin/zsh
PROJECT_DIR="/Users/arraymac/Desktop/project/CardHelper"
PORT=8765

if ! /usr/sbin/lsof -i :$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    cd "$PROJECT_DIR"
    /usr/bin/nohup /usr/bin/python3 "$PROJECT_DIR/server.py" </dev/null >/tmp/cardhelper_server.log 2>&1 &
    sleep 0.6
fi

/usr/bin/open "http://127.0.0.1:$PORT"
