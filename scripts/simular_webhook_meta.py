#!/usr/bin/env python3
"""Simula las llamadas que Meta hace al webhook de WhatsApp Cloud API.

Sirve para probar el flujo de n8n sin depender de Meta:
  - verificación GET (hub.challenge)
  - mensaje entrante POST firmado con X-Hub-Signature-256

Solo usa la biblioteca estándar. Los secretos se leen de variables de entorno,
nunca de argumentos (para que no queden en el historial del shell).

Ejemplos:
  export WHATSAPP_APP_SECRET=... WHATSAPP_VERIFY_TOKEN=... WHATSAPP_PHONE_NUMBER_ID=...
  python3 scripts/simular_webhook_meta.py verificar --url http://localhost:5678/webhook/whatsapp
  python3 scripts/simular_webhook_meta.py mensaje   --url http://localhost:5678/webhook/whatsapp \
      --desde 595981000000 --texto "Hola"
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def env(name):
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"Falta la variable de entorno {name}")
    return value


def request(method, url, body=None, headers=None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def payload_mensaje(phone_number_id, desde, texto, message_id, nombre):
    """Estructura del webhook 'messages' de WhatsApp Cloud API."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_ID_SIMULADO",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "000000000", "phone_number_id": phone_number_id},
                    "contacts": [{"profile": {"name": nombre}, "wa_id": desde}],
                    "messages": [{
                        "from": desde,
                        "id": message_id,
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": texto},
                    }],
                },
            }],
        }],
    }


def payload_estado(phone_number_id, desde):
    """Evento de estado (entregado/leído): el flujo NO debe responderlo."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_ID_SIMULADO",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "000000000", "phone_number_id": phone_number_id},
                    "statuses": [{
                        "id": f"wamid.SIM{uuid.uuid4().hex}",
                        "status": "delivered",
                        "timestamp": str(int(time.time())),
                        "recipient_id": desde,
                    }],
                },
            }],
        }],
    }


def post_firmado(url, payload, secret):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    firma = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return request("POST", url, body, {"Content-Type": "application/json", "X-Hub-Signature-256": firma})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("accion", choices=["verificar", "mensaje", "estado"])
    p.add_argument("--url", required=True, help="URL del webhook de n8n (…/webhook/whatsapp)")
    p.add_argument("--desde", default="595981000000", help="wa_id del remitente (solo dígitos)")
    p.add_argument("--texto", default="Mensaje de prueba")
    p.add_argument("--nombre", default="Alumno de prueba")
    p.add_argument("--message-id", default=None, help="Reutilizar un id para probar idempotencia")
    p.add_argument("--firma-invalida", action="store_true", help="Firmar con un secreto incorrecto")
    a = p.parse_args()

    if a.accion == "verificar":
        challenge = uuid.uuid4().hex
        qs = urllib.parse.urlencode({
            "hub.mode": "subscribe",
            "hub.verify_token": env("WHATSAPP_VERIFY_TOKEN"),
            "hub.challenge": challenge,
        })
        status, text = request("GET", f"{a.url}?{qs}")
        ok = status == 200 and text == challenge
        print(f"GET verificación -> {status} {text!r} ({'OK' if ok else 'FALLO'})")
        sys.exit(0 if ok else 1)

    secret = "secreto-incorrecto" if a.firma_invalida else env("WHATSAPP_APP_SECRET")
    phone_id = env("WHATSAPP_PHONE_NUMBER_ID")
    if a.accion == "mensaje":
        mid = a.message_id or f"wamid.SIM{uuid.uuid4().hex}"
        payload = payload_mensaje(phone_id, a.desde, a.texto, mid, a.nombre)
    else:
        mid = None
        payload = payload_estado(phone_id, a.desde)

    status, text = post_firmado(a.url, payload, secret)
    print(f"POST {a.accion} id={mid} -> {status} {text!r}")
    sys.exit(0 if status in (200, 401) else 1)


if __name__ == "__main__":
    main()
