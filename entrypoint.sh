#!/bin/sh
set -eu
: "${UUID:?UUID required}"
: "${SUB_TOKEN:?SUB_TOKEN required}"
export WS_PATH="${WS_PATH:-/ws}"
export XRAY_PORT="${XRAY_PORT:-10000}"
cat > /app/config.json <<EOF
{"log":{"loglevel":"warning"},
 "inbounds":[{"listen":"127.0.0.1","port":${XRAY_PORT},"protocol":"vless",
   "settings":{"clients":[{"id":"${UUID}"}],"decryption":"none"},
   "streamSettings":{"network":"ws","wsSettings":{"path":"${WS_PATH}"}}}],
 "outbounds":[{"protocol":"freedom","tag":"direct"}]}
EOF
/app/xray run -c /app/config.json &
exec python3 /app/front.py
