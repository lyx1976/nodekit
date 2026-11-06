FROM ghcr.io/xtls/xray-core:latest AS xray
FROM python:3.12-alpine
COPY --from=xray /usr/local/bin/xray /app/xray
COPY front.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh /app/xray
CMD ["/app/entrypoint.sh"]
