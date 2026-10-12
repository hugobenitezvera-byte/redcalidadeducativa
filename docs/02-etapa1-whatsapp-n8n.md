# Etapa 1: WhatsApp Cloud API ↔ n8n (recibir y responder un mensaje de prueba)

Objetivo: comprobar la conexión. Un alumno de prueba escribe al número de WhatsApp y n8n le
responde automáticamente `Recibido: "<su texto>"`. Esta etapa todavía no usa Django, IA ni la
base de datos académica.

## Qué se entrega

| Archivo | Para qué |
|---|---|
| `n8n/workflows/etapa1_whatsapp_prueba.json` | Workflow importable en n8n. |
| `n8n/docker-compose.yml` | n8n 2.42.7 (versión fijada) para pruebas o staging. |
| `n8n/.env.example` | Variables necesarias, sin valores. |
| `scripts/simular_webhook_meta.py` | Simula a Meta (GET de verificación y POST firmado). |
| `scripts/mock_graph_api.py` | Graph API falso para pruebas locales (no envía nada real). |
| `scripts/prueba_local_e2e.sh` | Prueba automática de punta a punta con n8n real en Docker. |

## Cómo funciona el workflow

```
GET  /webhook/whatsapp → valida hub.verify_token → 200 con hub.challenge  | 403
POST /webhook/whatsapp → valida X-Hub-Signature-256 (HMAC-SHA256 del cuerpo crudo con el App Secret)
                           ├─ inválida → 401
                           └─ válida   → 200 a Meta → extrae mensajes
                                          · ignora eventos de estado (enviado/entregado/leído)
                                          · ignora otros phone_number_id
                                          · descarta ids ya procesados (idempotencia)
                                          · responde solo a WA_TEST_ALLOWED_NUMBERS
                                        → POST {graph}/{versión}/{phone_number_id}/messages
                                          (3 intentos; si falla, la ejecución queda en error en n8n)
```

Medidas de seguridad de esta etapa:
- Secretos solo por variables de entorno; el token de acceso, como **credencial cifrada** de n8n.
- Firma de Meta validada con comparación en tiempo constante; sin firma válida no se procesa nada.
- Lista blanca de números: aunque se conecte un número real, la prueba **no responde a alumnos reales**.
- Si falta `WHATSAPP_PHONE_NUMBER_ID` o `WHATSAPP_APP_SECRET`, el flujo no responde (falla cerrado).

Limitación conocida (se resuelve en la Etapa 2): el 200 se envía a Meta antes de responder, y la
deduplicación vive en los datos estáticos de n8n (últimos 1000 ids). La fuente definitiva de
idempotencia será la base de datos del CRM.

## Paso 0: prueba local sin Meta (recomendado antes de nada)

Requiere Docker y Python 3.

```bash
bash scripts/prueba_local_e2e.sh
```

Resultado esperado:

```
OK    GET verificación devuelve el challenge
OK    GET con verify_token incorrecto -> 403
OK    POST sin firma -> 401
OK    POST con firma inválida -> 401
OK    Mensaje válido genera 1 respuesta
OK    Duplicado, estado y número no autorizado no responden
OK    Respuesta saliente con URL, token y cuerpo correctos
TODAS LAS PRUEBAS PASARON
```

El script usa `--network host` y no deja nada instalado (borra el contenedor al terminar).

## Paso 1: app de Meta y número de prueba

En <https://developers.facebook.com/apps>:

1. Crear una app de tipo empresa (Business) vinculada al portafolio comercial del instituto y
   agregarle el producto **WhatsApp**.
2. En **WhatsApp → Configuración de la API** (API Setup) anotar:
   - **Phone number ID** del número de prueba → `WHATSAPP_PHONE_NUMBER_ID`.
   - El **token de acceso temporal** (vence en ~24 h; alcanza para esta prueba).
   - En "Para" (To), **agregar y verificar** tu número personal: en modo de prueba Meta solo
     permite enviar a números verificados ahí.
3. En **Configuración de la app → Básica** copiar el **App Secret** → `WHATSAPP_APP_SECRET`.
4. Anotar la versión de Graph API que muestra el panel (p. ej. `v23.0`) → `WHATSAPP_GRAPH_VERSION`.

Usá el **número de prueba de Meta**. No conectes todavía el número oficial del instituto
(ver riesgos en `docs/01-analisis-y-plan.md`).

## Paso 2: levantar n8n con URL pública HTTPS

Meta solo llama a URLs **HTTPS con certificado válido**. Opciones:
- n8n en un servidor del instituto con dominio y proxy inverso (Nginx/Caddy) con TLS.
- Para una prueba rápida, un túnel temporal hacia `http://localhost:5678`
  (por ejemplo `cloudflared tunnel --url http://localhost:5678`).

Este workflow usa variables de entorno (`$env`), así que requiere **n8n autoalojado**
(n8n Cloud no permite variables de entorno propias).

```bash
cd n8n
cp .env.example .env
# completar .env: N8N_ENCRYPTION_KEY, WEBHOOK_URL (la URL HTTPS pública),
# WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN,
# WHATSAPP_GRAPH_VERSION y WA_TEST_ALLOWED_NUMBERS (tu número, solo dígitos con código de país)
docker compose up -d
```

Si ya tienen una instancia de n8n, no hace falta este compose: agregá a esa instancia las
variables de `.env.example` más `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` y
`NODE_FUNCTION_ALLOW_BUILTIN=crypto`, y reiniciala.

## Paso 3: importar el workflow y cargar el token

1. En n8n: **Credentials → Create → Header Auth**
   - Nombre: `WhatsApp Cloud API token`
   - Name: `Authorization`
   - Value: `Bearer <token de acceso de Meta>`
2. **Workflows → Import from file** → `n8n/workflows/etapa1_whatsapp_prueba.json`.
3. Abrir el nodo **"Enviar respuesta (WhatsApp Cloud API)"** y elegir la credencial del punto 1.
4. **Publicar/activar** el workflow. La URL de producción es `<WEBHOOK_URL>webhook/whatsapp`.

Verificación antes de ir a Meta (desde tu PC, con las mismas variables exportadas):

```bash
export WHATSAPP_VERIFY_TOKEN=...   # el mismo valor del .env
python3 scripts/simular_webhook_meta.py verificar --url https://TU-DOMINIO/webhook/whatsapp
# Esperado: GET verificación -> 200 '...' (OK)
```

## Paso 4: conectar el webhook en Meta

En la app de Meta → **WhatsApp → Configuración** (Configuration) → Webhook:

1. **URL de devolución de llamada**: `https://TU-DOMINIO/webhook/whatsapp`
2. **Token de verificación**: el valor de `WHATSAPP_VERIFY_TOKEN`.
3. **Verificar y guardar**. En n8n aparece una ejecución exitosa de la rama GET.
4. En **Campos del webhook**, suscribirse a **`messages`**.

## Paso 5: prueba real

Desde tu teléfono (verificado en el Paso 1 e incluido en `WA_TEST_ALLOWED_NUMBERS`), escribí
"Hola" al número de prueba. En segundos deberías recibir:

```
Recibido: "Hola"

Prueba de conexión WhatsApp - n8n OK.
```

En n8n → **Executions** vas a ver una ejecución por cada aviso de Meta: los avisos de estado
(enviado/entregado/leído) también llegan y terminan sin responder; eso es lo correcto.

Comprobaciones adicionales:

| Prueba | Resultado esperado |
|---|---|
| Escribir desde un número que no está en `WA_TEST_ALLOWED_NUMBERS` | Sin respuesta. |
| Enviar una imagen o audio | Mensaje "solo respondo mensajes de texto". |
| `python3 scripts/simular_webhook_meta.py mensaje --url ... --firma-invalida` | `401`. |

## Solución de problemas

| Síntoma | Causa probable |
|---|---|
| Meta no puede verificar la URL | URL no pública o sin HTTPS válido, workflow no activado, o `WHATSAPP_VERIFY_TOKEN` distinto. |
| Todas las ejecuciones POST terminan en 401 | `WHATSAPP_APP_SECRET` incorrecto (es el de la app, no el token) o un proxy que modifica el cuerpo. |
| Llega el mensaje pero no hay respuesta | Número fuera de la lista blanca, `WHATSAPP_PHONE_NUMBER_ID` distinto, o falta elegir la credencial. |
| Error en "Enviar respuesta" con código 190 | Token vencido o inválido: generar uno nuevo y actualizar la credencial. |
| Error 131030 | El número destino no está verificado en la lista "Para" del número de prueba. |
| Error en nodo Code: `$env` / `crypto` no permitido | Faltan `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` o `NODE_FUNCTION_ALLOW_BUILTIN=crypto`. |

## Cómo deshacer

Desactivar el workflow en n8n y quitar la URL del webhook en Meta. Nada de esta etapa toca el
sistema académico ni su base de datos.
