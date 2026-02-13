#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY=""
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PY="$ROOT/venv/bin/python"
fi

if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
    PY="$ROOT/.venv/bin/python"
  elif command -v python >/dev/null 2>&1; then
    python -m venv .venv
    PY="$ROOT/.venv/bin/python"
  else
    echo "Python nao encontrado. Instale Python 3.10+ antes de rodar."
    exit 1
  fi

  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r App/requirements.txt
fi

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
UI_HOST="${UI_HOST:-0.0.0.0}"
UI_PORT="${UI_PORT:-8501}"

API_BASE="${API_BASE:-}"
if [ -n "$API_BASE" ]; then
  if command -v python3 >/dev/null 2>&1; then
    API_PORT=$(python3 - <<'PY'
import os
from urllib.parse import urlparse
url = os.environ.get("API_BASE", "")
try:
    print(urlparse(url).port or 8000)
except Exception:
    print(8000)
PY
    )
  fi
else
  API_BASE="http://127.0.0.1:${API_PORT}"
fi

if [ "${SKIP_PLAYWRIGHT_INSTALL:-0}" != "1" ]; then
  echo "Verificando browser do Playwright (chromium)..."
  if ! "$PY" -m playwright install chromium >/tmp/playwright-install.log 2>&1; then
    echo "AVISO: falha ao instalar Chromium do Playwright. Veja /tmp/playwright-install.log"
  fi
fi

if [ -z "${API_TOKEN:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    API_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
  else
    API_TOKEN="$(date +%s)-$(hostname)"
  fi
  export API_TOKEN
  echo "API_TOKEN temporario gerado para esta sessao."
fi

health_check() {
  curl -fsS --max-time 2 "$API_BASE/api/health" >/dev/null 2>&1
}

if ! health_check; then
  echo "Iniciando API em ${API_HOST}:${API_PORT}..."
  "$PY" -m uvicorn ui.server:app --host "$API_HOST" --port "$API_PORT" >/tmp/uvicorn.log 2>&1 &
  sleep 2
fi

if [ -z "${APP_AUTH_USER:-}" ] || [ -z "${APP_AUTH_PASSWORD:-}" ]; then
  echo "AVISO: APP_AUTH_USER/APP_AUTH_PASSWORD nao definidos. Defina para proteger acesso remoto da UI."
fi

export API_BASE

echo "Acesso local: http://localhost:${UI_PORT}"
if command -v hostname >/dev/null 2>&1; then
  for ip in $(hostname -I 2>/dev/null || true); do
    echo "Acesso remoto (rede): http://${ip}:${UI_PORT}"
  done
fi

STREAMLIT_ARGS=(
  -m streamlit run ui_streamlit/app.py
  --server.address "$UI_HOST"
  --server.port "$UI_PORT"
)

if [ -n "${SSL_CERT_FILE:-}" ] && [ -n "${SSL_KEY_FILE:-}" ] && [ -f "$SSL_CERT_FILE" ] && [ -f "$SSL_KEY_FILE" ]; then
  STREAMLIT_ARGS+=(--server.sslCertFile "$SSL_CERT_FILE" --server.sslKeyFile "$SSL_KEY_FILE")
  echo "HTTPS habilitado para Streamlit."
elif [ -n "${SSL_CERT_FILE:-}" ] || [ -n "${SSL_KEY_FILE:-}" ]; then
  echo "AVISO: SSL_CERT_FILE/SSL_KEY_FILE invalidos. Iniciando sem HTTPS."
fi

exec "$PY" "${STREAMLIT_ARGS[@]}"
