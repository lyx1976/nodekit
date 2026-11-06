#!/usr/bin/env python3
"""Front server for PaaS xray node.
Listens on $PORT. Routes:
 - $WS_PATH (websocket upgrade) -> raw TCP tunnel to xray on 127.0.0.1:$XRAY_PORT
 - /$SUB_TOKEN/sub   -> Shadowrocket subscription (base64 of vless link), host built from request Host
 - /$SUB_TOKEN/clash -> Clash YAML, host built from request Host
 - /$SUB_TOKEN/vless -> raw vless:// link
 - /                 -> plain 200 camouflage
Everything else 404. Stdlib only.
"""
import os, base64, socket, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, quote

UUID = os.environ["UUID"]
WS_PATH = os.environ.get("WS_PATH", "/ws")
SUB_TOKEN = os.environ["SUB_TOKEN"]
XRAY_PORT = int(os.environ.get("XRAY_PORT", "10000"))
NODE_NAME = os.environ.get("NODE_NAME", "MuseX-Node")

def vless_link(host):
    p = quote(WS_PATH, safe="")
    return (f"vless://{UUID}@{host}:443?encryption=none&security=tls&type=ws"
            f"&host={host}&path={p}#{quote(NODE_NAME)}")

def clash_yaml(host):
    providers = ["LocalAreaNetwork", "UnBan", "BanAD", "BanProgramAD", "Apple", "ChinaMedia", "ChinaDomain"]
    prov = "\n".join(
        f"  {n}:\n    type: http\n    behavior: classical\n"
        f"    url: https://cdn.jsdelivr.net/gh/ACL4SSR/ACL4SSR@master/Clash/Providers/{n}.list\n"
        f"    path: ./ruleset/{n}.list\n    interval: 86400" for n in providers)
    return f"""mixed-port: 7890
allow-lan: false
mode: rule
log-level: info
ipv6: false
external-controller: 127.0.0.1:9090
dns:
  enable: true
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  default-nameserver: [223.5.5.5, 119.29.29.29]
  nameserver: [223.5.5.5, 119.29.29.29]
  fake-ip-filter: ['*.lan', '*.local', 'time.*.com', 'ntp.*.com', '+.msftconnecttest.com', '+.msftncsi.com']
proxies:
  - name: "{NODE_NAME}"
    type: vless
    server: {host}
    port: 443
    uuid: {UUID}
    udp: true
    tls: true
    servername: {host}
    network: ws
    ws-opts:
      path: "{WS_PATH}"
      headers:
        Host: {host}
proxy-groups:
  - name: "\U0001F680 手动选择"
    type: select
    proxies: ["{NODE_NAME}", DIRECT]
rules:
  - RULE-SET,LocalAreaNetwork,DIRECT
  - RULE-SET,UnBan,DIRECT
  - RULE-SET,BanAD,REJECT
  - RULE-SET,BanProgramAD,REJECT
  - RULE-SET,Apple,DIRECT
  - RULE-SET,ChinaMedia,DIRECT
  - RULE-SET,ChinaDomain,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,\U0001F680 手动选择
keep-alive-interval: 15
keep-alive-idle: 15
rule-providers:
{prov}
"""

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        path = urlparse(self.path).path
        host = self.headers.get("Host", "localhost").split(":")[0]
        if path == f"/{SUB_TOKEN}/sub":
            raw = vless_link(host) + "\n"
            self._send(200, base64.b64encode(raw.encode()).decode())
        elif path == f"/{SUB_TOKEN}/clash":
            self._send(200, clash_yaml(host), "text/yaml; charset=utf-8")
        elif path == f"/{SUB_TOKEN}/vless":
            self._send(200, vless_link(host) + "\n")
        elif path == WS_PATH and self.headers.get("Upgrade", "").lower() == "websocket":
            self._tunnel()
        elif path == "/":
            self._send(200, "ok")
        else:
            self._send(404, "not found")
    def _tunnel(self):
        try:
            up = socket.create_connection(("127.0.0.1", XRAY_PORT), timeout=10)
        except OSError:
            self._send(502, "bad gateway"); return
        # rebuild request head
        lines = [f"GET {self.path} HTTP/1.1"]
        for k, v in self.headers.items():
            lines.append(f"{k}: {v}")
        head = ("\r\n".join(lines) + "\r\n\r\n").encode()
        up.sendall(head)
        conn = self.connection
        conn.setblocking(False); up.setblocking(False)
        import select
        socks = [conn, up]
        try:
            while True:
                r, _, x = select.select(socks, [], socks, 60)
                if x or not r: break
                done = False
                for s in r:
                    try: data = s.recv(65536)
                    except OSError: data = b""
                    if not data: done = True; break
                    (up if s is conn else conn).sendall(data)
                if done: break
        finally:
            try: up.close()
            except OSError: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
