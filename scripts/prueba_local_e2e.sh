#!/usr/bin/env bash
# Prueba local de punta a punta del flujo de la Etapa 1, SIN tocar Meta:
# levanta n8n (Docker) + un Graph API falso, importa el workflow y verifica
# verificación GET, firma, idempotencia, filtros y respuesta saliente.
# Uso: bash scripts/prueba_local_e2e.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="n8nio/n8n:2.42.7"
NAME="n8n-crm-e2e"
WORK="$(mktemp -d)"
URL="http://localhost:5678/webhook/whatsapp"
SIM="$ROOT/scripts/simular_webhook_meta.py"

export WHATSAPP_APP_SECRET="app-secret-de-prueba"
export WHATSAPP_VERIFY_TOKEN="verify-token-de-prueba"
export WHATSAPP_PHONE_NUMBER_ID="111222333444555"
ALLOWED="595981000000"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  [ -n "${MOCK_PID:-}" ] && kill "$MOCK_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

cat > "$WORK/test.env" <<ENV
N8N_ENCRYPTION_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
N8N_LISTEN_ADDRESS=0.0.0.0
WEBHOOK_URL=http://localhost:5678/
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
NODE_FUNCTION_ALLOW_BUILTIN=crypto
N8N_DIAGNOSTICS_ENABLED=false
WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_APP_SECRET=$WHATSAPP_APP_SECRET
WHATSAPP_VERIFY_TOKEN=$WHATSAPP_VERIFY_TOKEN
WHATSAPP_GRAPH_VERSION=v23.0
WHATSAPP_GRAPH_BASE_URL=http://127.0.0.1:9999
WA_TEST_ALLOWED_NUMBERS=$ALLOWED
ENV
cat > "$WORK/cred.json" <<'JSON'
[{"id":"WA_CLOUD_API_TOKEN","name":"WhatsApp Cloud API token","type":"httpHeaderAuth",
  "data":{"name":"Authorization","value":"Bearer TOKEN_FALSO_E2E"}}]
JSON

python3 "$ROOT/scripts/mock_graph_api.py" --puerto 9999 --log "$WORK/graph_calls.jsonl" >/dev/null 2>&1 &
MOCK_PID=$!

wait_healthy() {
  for _ in $(seq 1 90); do
    curl -sf -o /dev/null localhost:5678/healthz && return 0
    sleep 2
  done
  docker logs "$NAME" | tail -20; exit 1
}

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --network host --env-file "$WORK/test.env" \
  -v "$ROOT/n8n/workflows:/wf:ro" -v "$WORK/cred.json:/cred.json:ro" "$IMAGE" >/dev/null
wait_healthy
docker exec "$NAME" n8n import:credentials --input=/cred.json >/dev/null
docker exec "$NAME" n8n import:workflow --input=/wf/etapa1_whatsapp_prueba.json >/dev/null
docker exec "$NAME" n8n publish:workflow --id=crmEtapa1WhatsApp >/dev/null
docker restart "$NAME" >/dev/null
wait_healthy
# El webhook se registra unos segundos después de que /healthz responde.
for _ in $(seq 1 30); do
  python3 "$SIM" verificar --url "$URL" >/dev/null 2>&1 && break
  sleep 2
done

FAIL=0
check() { # descripción, esperado, obtenido
  if [ "$2" = "$3" ]; then echo "OK    $1"; else echo "FALLO $1 (esperado $2, obtenido $3)"; FAIL=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
calls() { [ -f "$WORK/graph_calls.jsonl" ] && wc -l < "$WORK/graph_calls.jsonl" | tr -d ' ' || echo 0; }

python3 "$SIM" verificar --url "$URL" >/dev/null && R=ok || R=fallo
check "GET verificación devuelve el challenge" ok "$R"
check "GET con verify_token incorrecto -> 403" 403 "$(code "$URL?hub.mode=subscribe&hub.verify_token=malo&hub.challenge=1")"
check "POST sin firma -> 401" 401 "$(code -X POST -H 'Content-Type: application/json' -d '{}' "$URL")"
python3 "$SIM" mensaje --url "$URL" --firma-invalida | grep -q ' 401 ' && R=401 || R=otro
check "POST con firma inválida -> 401" 401 "$R"

python3 "$SIM" mensaje --url "$URL" --desde "$ALLOWED" --texto "Hola ñandú" --message-id wamid.E2E1 >/dev/null
sleep 3; check "Mensaje válido genera 1 respuesta" 1 "$(calls)"
python3 "$SIM" mensaje --url "$URL" --desde "$ALLOWED" --texto "Hola ñandú" --message-id wamid.E2E1 >/dev/null
python3 "$SIM" estado --url "$URL" >/dev/null
python3 "$SIM" mensaje --url "$URL" --desde 595991999999 >/dev/null
sleep 3; check "Duplicado, estado y número no autorizado no responden" 1 "$(calls)"

R=$(python3 - "$WORK/graph_calls.jsonl" <<'PY'
import json, sys
c = json.loads(open(sys.argv[1], encoding="utf-8").readline())
b = c["body"]
ok = (c["path"] == "/v23.0/111222333444555/messages" and c["authorization"] == "Bearer TOKEN_FALSO_E2E"
      and b["to"] == "595981000000" and b["type"] == "text" and "Hola ñandú" in b["text"]["body"])
print("ok" if ok else json.dumps(c, ensure_ascii=False))
PY
)
check "Respuesta saliente con URL, token y cuerpo correctos" ok "$R"

[ "$FAIL" = 0 ] && echo "TODAS LAS PRUEBAS PASARON" || { echo "HAY FALLOS"; exit 1; }
