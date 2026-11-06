#!/bin/sh
# Route A: runtime wrapper for panels that only give a runtime + file upload.
# Downloads official xray-core release at startup, builds config from env, launches.
set -eu
: "${UUID:?}"; : "${SUB_TOKEN:?}"
export WS_PATH="${WS_PATH:-/ws}" XRAY_PORT="${XRAY_PORT:-10000}"
cd "$(dirname "$0")"
if [ ! -x ./xray ]; then
  VER="${XRAY_VERSION:-v25.3.6}"
  wget -qO xray.zip "https://github.com/XTLS/Xray-core/releases/download/${VER}/Xray-linux-64.zip"
  unzip -oq xray.zip xray && chmod +x ./xray && rm -f xray.zip
fi
sed -e "s/__UUID__/${UUID}/g" -e "s/__WSPATH__/${WS_PATH}/g" -e "s/__XRAYPORT__/${XRAY_PORT}/g" config.template.json > config.json
./xray run -c config.json &
exec python3 front.py
