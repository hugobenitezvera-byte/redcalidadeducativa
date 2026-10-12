#!/usr/bin/env python3
"""Servidor falso de Graph API para pruebas locales (no envía nada a Meta).

Registra cada POST /<version>/<phone_number_id>/messages en un archivo JSONL
y responde como lo haría la Cloud API. Usar junto con
WHATSAPP_GRAPH_BASE_URL=http://<host>:<puerto> en n8n.

  python3 scripts/mock_graph_api.py --puerto 9999 --log /tmp/graph_calls.jsonl
"""
import argparse
import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--puerto", type=int, default=9999)
    p.add_argument("--log", default="graph_calls.jsonl")
    a = p.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            with open(a.log, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "path": self.path,
                    "authorization": self.headers.get("Authorization", ""),
                    "body": json.loads(body or b"{}"),
                }, ensure_ascii=False) + "\n")
            resp = json.dumps({
                "messaging_product": "whatsapp",
                "contacts": [{"input": "", "wa_id": ""}],
                "messages": [{"id": f"wamid.MOCK{uuid.uuid4().hex}"}],
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)

        def log_message(self, *args):
            pass

    print(f"Mock Graph API escuchando en :{a.puerto}, registrando en {a.log}")
    HTTPServer(("0.0.0.0", a.puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
