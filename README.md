# CRM de atención al alumno — Red Calidad Educativa

Plataforma de atención al alumno por WhatsApp (Cloud API de Meta) con n8n, IA y un CRM en Django.
Se construye por etapas; cada etapa se verifica antes de pasar a la siguiente.

| Documento | Contenido |
|---|---|
| [docs/01-analisis-y-plan.md](docs/01-analisis-y-plan.md) | Análisis del repositorio, componentes reutilizables, plan por etapas, riesgos y pruebas. |
| [docs/02-etapa1-whatsapp-n8n.md](docs/02-etapa1-whatsapp-n8n.md) | Etapa 1: conectar WhatsApp Cloud API con n8n y responder un mensaje de prueba. |
| [docs/03-datos-csv.md](docs/03-datos-csv.md) | Datos iniciales en CSV (carreras/aranceles, alumnos, materias), verificación de identidad y plantillas ficticias. |

Estado: **Etapa 1** implementada y probada localmente (`bash scripts/prueba_local_e2e.sh`).
Pendiente la prueba con Meta.

`index.html` (y sus copias `index.htm`, `index.html.htm`) es el manual actual de casos de atención;
se usará como catálogo de motivos y base de respuestas generales en etapas posteriores.

Nunca commitear archivos `.env` ni tokens: este repositorio es público.
