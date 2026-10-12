# CRM de atención al alumno: análisis inicial y plan por etapas

Fecha del análisis: 2026-10-12. Rama: `claude/crm-student-support-ep56r0`.

## 1. Arquitectura actual (lo que hay en el repositorio)

Revisé el repositorio `hugobenitezvera-byte/redcalidadeducativa` completo y la lista de repositorios
a los que esta sesión tiene acceso (solo este).

| Archivo | Contenido |
|---|---|
| `index.html`, `index.htm`, `index.html.htm` | Tres copias **idénticas** (mismo MD5) de un documento de Word exportado a HTML (codificación windows-1252). |

**No hay código Django en este repositorio**: no hay `manage.py`, `settings.py`, modelos, migraciones,
`requirements.txt` ni plantillas. Por lo tanto **no pude inspeccionar el sistema académico** y,
como pediste, no invento nombres de tablas, campos ni endpoints. Todo lo que dependa del sistema
académico queda marcado como "a confirmar".

El documento HTML sí es valioso: es el **manual de casos de atención** que hoy resuelve el personal.
Contiene:

- Consultas de coordinadores: habilitar plataforma, no puede acceder, no le aparecen materias,
  habilitar tarea/otro intento, docente no sube materiales, materias no coinciden, titulación,
  retomar, documentos a entregar, planilla de pasantía, calificaciones antiguas (MEC),
  certificados antiguos, desmatriculación, constancias, "cereo" de exámenes parciales,
  activación de cuenta, retiro de títulos.
- Tesorería: facturación por red Infonet/vPOS (sede de facturación), orden de vencimientos
  cuota / derecho de examen.
- Listado de solicitudes: activación de usuario, actualizar estado de cuenta, eliminar/cargar
  derecho de examen, cambio de sede, cambio de inscripción, desmatriculación.
- Postulantes: habilitación de carreras (MEC para pregrado, CONES para grado/postgrado).
- Para varios casos se pide la **cédula de identidad (CI)** para verificar al alumno.
- Menciona "Tinkchat" como canal donde hoy quedan consultas sin respuesta.

## 2. Componentes reutilizables

| Componente | Uso en el CRM | Estado |
|---|---|---|
| Autenticación de Django (`django.contrib.auth`, sesiones, login) | Login de los 5 funcionarios, sin cuentas nuevas | A confirmar en el código del sistema académico |
| Grupos y permisos de Django | Roles: Funcionario, Supervisor, Administrador | A confirmar |
| Plantilla base / layout del frontend existente | Pantallas de bandeja, ficha, tickets y dashboard | A confirmar |
| Django admin | Administración inicial de catálogos (motivos, prioridades) | A confirmar |
| Modelos de alumno, inscripción, materias, estado de cuenta | Funciones controladas de consulta (solo lectura) | **Desconocidos**: necesito el código |
| Manual de casos (`index.html`) | Catálogo de **motivos** de ticket y base de respuestas generales (no personales) para la IA | Disponible |
| CI como dato de verificación | Paso de identificación del alumno | Disponible (como práctica), el campo real está por confirmar |

## 3. Modelos y aplicaciones existentes

No se pueden listar: el código no está en este repositorio. Para avanzar a la Etapa 2 necesito
**una** de estas opciones:

1. Agregar el repositorio del sistema académico a esta sesión (o darme acceso), **o**
2. Que me compartas la salida de estos comandos, ejecutados en un entorno que NO sea producción:
   ```bash
   python --version
   python -m django --version
   python manage.py showmigrations        # lista apps y migraciones
   python manage.py inspectdb --help >/dev/null && echo ok   # solo para confirmar acceso
   ```
   y los archivos `settings.py` (sin secretos), `urls.py` raíz y los `models.py` de las apps que
   contienen alumnos, inscripciones, materias y estado de cuenta.

## 4. Cambios mínimos necesarios (propuesta, a validar con el código real)

- **Una app Django nueva, `crm`, dentro del proyecto existente**, para reutilizar login, usuarios,
  permisos y plantillas. Sus tablas serán nuevas (prefijo `crm_`) y sus migraciones **solo aditivas**
  (crear tablas). No se modifica ni se borra ninguna tabla académica.
- Acceso a datos académicos y financieros **solo de lectura**, a través de un módulo de servicios
  (`crm/servicios/academico.py`) con funciones explícitas (p. ej. "materias que cursa el alumno X").
  La IA nunca ve SQL ni modelos: solo puede pedir esas funciones, con el alumno ya verificado.
- Endpoints internos para n8n autenticados con secreto compartido (HMAC), separados de los de usuarios.
- Django será la **fuente de verdad** de conversaciones y mensajes, y el **único que envía** mensajes
  salientes, verificando el estado de la conversación con bloqueo de fila. Así se evita que la IA y un
  funcionario respondan a la vez.
- n8n orquesta: recibe el webhook de Meta, llama a Django y a la IA.

Flujo objetivo (desde la Etapa 2):

```
Alumno ──WhatsApp──► Meta Cloud API ──webhook firmado──► n8n
                                                          │ 1. valida firma
                                                          │ 2. POST /crm/... (Django guarda; UNIQUE por id de mensaje)
                                                          │ 3. recién entonces responde 200 a Meta
                                                          ▼
                            Django CRM decide: ¿conversación en manos de un funcionario?
                               ├─ sí → no hay IA; aparece en la bandeja del funcionario
                               └─ no → n8n pide respuesta a la IA (con herramientas = funciones controladas)
                                        └─ la IA no puede resolver → Django crea ticket PENDIENTE en la cola
Salida: Django → Cloud API (registra el mensaje; rechaza respuestas de la IA si hay un humano asignado)
```

## 5. Plan por etapas

| Etapa | Alcance | Criterio de "listo" |
|---|---|---|
| **1 (esta)** | WhatsApp Cloud API ↔ n8n: verificar el webhook, recibir un mensaje y responderlo. Firma, idempotencia básica, lista blanca de números de prueba. | Escribís al número de prueba y recibís la respuesta automática. Ver `docs/02-etapa1-whatsapp-n8n.md`. |
| 2 | App `crm` en Django: Contacto, Conversación, Mensaje (id de WhatsApp único), endpoint de ingreso desde n8n, envío saliente centralizado, admin. Sin IA. | Todo mensaje entrante y saliente queda guardado una sola vez; Meta reintenta si Django no guardó. |
| 3 | Menú MVP (inscripciones, materias, estado de cuenta, hablar con asesor) e identificación del alumno (CI + verificación adicional a definir). Funciones de solo lectura sobre los modelos reales. | Un alumno verificado consulta sus 3 datos; un no verificado no obtiene datos personales. |
| 4 | Tickets y bandeja humana: estados PENDIENTE / EN_ATENCION / CERRADA, motivo, prioridad, asignación atómica ("tomar"), respuesta por Cloud API, cierre con resultado, "devolver a la IA", roles y auditoría. | Dos funcionarios no pueden tomar el mismo chat; con chat asignado la IA no responde. |
| 5 | Asistente IA (Claude u otro, configurable) con *tool use* limitado a las funciones controladas y a la base de respuestas generales del manual. Escala a ticket cuando no puede resolver. | La IA no inventa datos personales; ante duda, crea ticket. |
| 6 | Dashboard, reportes, tiempos de atención, endurecimiento y salida a producción (token permanente, número definitivo, plantillas aprobadas). | Checklist de producción aprobado por vos. |

Propuesta de modelo para la Etapa 4 (a confirmar con vos): separar la **conversación** (hilo
permanente con el contacto) de la **atención/ticket** (cada episodio con motivo, prioridad, estado,
funcionario, fechas de creación/asignación/cierre y resultado). La IA queda pausada mientras exista
una atención abierta (PENDIENTE o EN_ATENCION) y se reactiva solo con la acción "devolver a la IA"
o al cerrar.

## 6. Riesgos y pruebas necesarias

### Riesgos

| Riesgo | Mitigación |
|---|---|
| No tengo el código del sistema académico | Bloquea la Etapa 3. La Etapa 1 no depende de él. |
| **El repositorio es público** | Ningún secreto en el repo (`.gitignore`, `.env.example`). Además, el manual `index.html` tiene procedimientos internos y nombres de personas: conviene pasar el repo a **privado**. |
| Número de WhatsApp ya conectado a otro proveedor (¿Tinkchat?) o a la app WhatsApp Business | Un número solo puede estar en un proveedor de API a la vez. Probar primero con el **número de prueba de Meta**; migrar el número real solo con un plan aprobado. |
| Ventana de 24 h de WhatsApp | Fuera de las 24 h desde el último mensaje del alumno solo se pueden enviar **plantillas aprobadas**. Afecta respuestas tardías de funcionarios (Etapa 4). |
| Token temporal de Meta (vence en ~24 h) | Para uso continuo: token de **usuario del sistema** del Business Manager, guardado como credencial cifrada. |
| Reintentos y duplicados de Meta | Etapa 1: deduplicación en n8n. Etapa 2: restricción UNIQUE en base de datos (fuente definitiva). |
| Pérdida de mensajes: en la Etapa 1 n8n responde 200 antes de procesar | Aceptable para la prueba. En la Etapa 2 el 200 se envía **después** de que Django guardó el mensaje. |
| Respuestas simultáneas de IA y funcionario | Envío centralizado en Django con bloqueo de fila y verificación de estado (Etapa 4). |
| Suplantación: el número de teléfono no prueba identidad | Verificación con CI + dato adicional; nunca datos personales sin verificación (Etapa 3). |
| IA que inventa información | Solo herramientas controladas + base de respuestas aprobadas; si no hay dato, ticket (Etapa 5). |
| Datos personales y financieros | Mínimo dato necesario, permisos por rol, auditoría de accesos, normativa local de protección de datos. |
| Migraciones en la base de producción | Solo aditivas, primero en una copia/staging, con respaldo previo y tu aprobación explícita. |
| `$env` habilitado en n8n | Cualquiera que edite flujos en n8n puede leer esas variables: limitar quién administra n8n. El token de Meta va como credencial cifrada, no en `$env`. |

### Pruebas

- **Etapa 1 (automatizadas, incluidas)**: `scripts/prueba_local_e2e.sh` levanta n8n real en Docker y
  un Graph API falso y verifica: verificación GET correcta e incorrecta, POST sin firma / con firma
  inválida (401), mensaje válido (1 respuesta), duplicado, evento de estado y número no autorizado
  (0 respuestas), y que la respuesta saliente lleve URL, token y cuerpo correctos.
- **Etapa 1 (manual con Meta)**: pasos en `docs/02-etapa1-whatsapp-n8n.md`.
- Etapas siguientes: pruebas unitarias Django (idempotencia, permisos por rol, toma concurrente
  con dos sesiones, bloqueo de la IA), pruebas de las funciones controladas con alumnos de prueba,
  y una batería de preguntas para la IA (incluidas preguntas trampa sobre datos de terceros).

## 7. Lo que necesito de vos para seguir

1. Acceso al código del sistema académico en Django (o la información de la sección 3).
2. Dónde va a correr n8n (servidor propio con dominio HTTPS, VPS, etc.) y si ya existe una instancia.
3. Qué número de WhatsApp se usará y si hoy está conectado a otro proveedor o a la app WhatsApp Business.
4. Si el portafolio comercial (Business Manager) de Meta del instituto ya está verificado.
