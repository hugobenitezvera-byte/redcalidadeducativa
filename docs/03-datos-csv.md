# Fuente de datos inicial: archivos CSV exportados

Fecha: 2026-10-13. Define qué datos entran al CRM mientras no esté integrado con el sistema
académico (ver sección 4 de `01-analisis-y-plan.md`).

## Datos confirmados

| Archivo | Contenido confirmado | Uso en el CRM | ¿Requiere verificar identidad? |
|---|---|---|---|
| Carreras y aranceles | Todas las carreras con sus aranceles | Opción **Inscripciones** del menú: carreras disponibles y costos. Sirve también para postulantes. | **No**: es información general. |
| Alumnos | Incluye **teléfono** y **correo** | Identificar al alumno que escribe y verificar su identidad. | Es la base de la verificación. |
| Materias por alumno | Qué materias lleva cada alumno | Opción **Materias cursando**. | **Sí**. |

Formato: **CSV**.

## Pendiente: estado de cuenta

Las exportaciones confirmadas traen los aranceles **por carrera**, pero no la **deuda ni los pagos
de cada alumno**. Sin ese dato, la opción **Estado de cuenta** del menú no puede responder de forma
automática. Opciones:

1. Exportar además un CSV de estado de cuenta por alumno (cuotas vencidas, montos, pagos), **o**
2. En el MVP, que "Estado de cuenta" cree directamente un ticket para tesorería con el alumno ya
   identificado. Es seguro y no requiere más datos.

Si no hay respuesta, se toma la opción 2.

## Verificación de identidad propuesta

Como el CSV de alumnos trae teléfono y correo:

1. El número de WhatsApp que escribe se compara con el **teléfono registrado** (normalizado:
   `0981 000 000` y `+595 981 000000` se comparan como `595981000000`).
2. Coincide → se pide además la **CI**. Si la CI corresponde a ese teléfono, el alumno queda
   verificado por un tiempo limitado (p. ej. 30 minutos de conversación).
3. No coincide (cambió de número, escribe un familiar) → se pide la CI y se envía un **código de un
   solo uso al correo registrado**. El alumno lo escribe en WhatsApp para verificarse.
4. Nunca se muestran datos personales sin verificación, ni se confirma si una CI existe.

## Formato de los CSV

Lo ideal es usar los **encabezados reales** de su exportación: el importador los traduce mediante un
archivo de configuración, sin cambiar código. Para eso necesito **solo la primera fila (encabezados)**
de cada CSV.

Si al exportar pueden elegir columnas, en `docs/plantillas-csv/` hay plantillas con datos
**ficticios** con el formato que propongo para el CRM:

- `carreras_aranceles.csv`: una fila por carrera, sede, modalidad y concepto. Va por sede porque el
  manual de atención indica que cada centro tiene su arancel.
- `alumnos.csv`: CI, nombres, teléfono, correo, carrera, sede, modalidad, semestre y estado.
- `materias_alumno.csv`: una fila por alumno, período y materia.

Estos nombres de columnas son la propuesta del CRM, **no** los del sistema académico.

El importador va a manejar:
- Separador `;` o `,` (Excel en español suele exportar con `;`).
- Codificación UTF-8 o Windows-1252.
- CI con o sin puntos, y teléfonos en distintos formatos.
- Validación previa: si el archivo tiene errores, se informa la fila y **no** se reemplazan los datos
  vigentes.

## Manejo de los archivos reales

- No se suben al repositorio (el `.gitignore` los bloquea). No compartirlos por chat ni por correo
  sin cifrar.
- Se cargan en el servidor del CRM, se importan y se borran.
- Cada importación registra la fecha de corte; el bot la informa ("datos al 13/10/2026").
