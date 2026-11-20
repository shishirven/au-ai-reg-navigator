#!/bin/sh
# Listen on $PORT. Cloud Run sets PORT (8080). Local Docker and compose leave it
# unset and get 8501, which is the port compose publishes.
#
# Cloud Run's proxy terminates TLS and forwards the browser's websocket.
# Streamlit's CORS and XSRF checks reject that proxied socket, so both are off.
# Websocket compression is off so the proxy does not have to speak permessage-deflate.
# The file watcher is off so Chroma's WAL files cannot restart the process.
set -eu
PORT="${PORT:-8501}"
exec streamlit run app/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT}" \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.enableWebsocketCompression=false \
  --server.fileWatcherType=none \
  --browser.gatherUsageStats=false
