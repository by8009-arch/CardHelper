#!/bin/zsh
PROJECT_DIR="/Users/arraymac/Desktop/project/CardHelper"
APP_PATH="/Users/arraymac/Desktop/CardHelper.app"

# 1. Apply custom icon to Desktop CardHelper.app
if [ -d "$APP_PATH" ]; then
    cp -f "$PROJECT_DIR/AppIcon.icns" "$APP_PATH/Contents/Resources/applet.icns"
    /tmp/set_app_icon
    touch "$APP_PATH"
fi

# 2. Restart server.py so new endpoints/fields take effect
PID=$(/usr/sbin/lsof -t -i :8765 -sTCP:LISTEN 2>/dev/null)
if [ -n "$PID" ]; then
    kill -9 $PID 2>/dev/null || true
    sleep 0.3
fi

cd "$PROJECT_DIR"
/usr/bin/nohup /usr/bin/python3 "$PROJECT_DIR/server.py" </dev/null >/tmp/cardhelper_server.log 2>&1 &
sleep 0.5
/usr/bin/open "http://127.0.0.1:8765"
