# Fuente de datos inicial: CSV exportados del sistema académico

Actualizado: 2026-10-13, con las tres exportaciones reales que recibí (`alumno.csv`, `cursos.csv`,
`aranceles.csv`). Aquí solo se documenta su **estructura** y estadísticas agregadas: ningún dato
personal se copia al repositorio.

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Formato | CSV exportado de PostgreSQL: separador coma, comillas dobles, UTF-8, nulos como `NULL`, booleanos `True`/`False`. |
| Frecuencia | **Una vez por mes.** Cada importación guarda su fecha de corte, y el bot la informa. |
| Estado de cuenta | El bot **no** muestra saldos. Si el alumno solo quiere consultarlo, el bot le indica el portal `app.redcalidadeducativa.edu.py`. Si tiene un reclamo o un problema (pago no reflejado, error en la cuota, etc.), crea un **ticket para el área de Cobranzas**. |
| Inscripciones | Carreras disponibles y aranceles, desde `aranceles.csv` + catálogos con nombres (los envía el instituto). Información general, sin verificar identidad. Si la persona quiere inscribirse, se crea un **ticket para el área de Admisión** con su nombre, teléfono y la carrera de interés. |
| `alumno.csv` | Se usa solo para tener la CI y los datos de contacto del alumno (identificación). |
| `activo` | `False` significa que el alumno está **inactivo o tiene alguna deuda** (ver abajo cómo lo usa el bot). |
| Nivel de inscripción distinto del nivel del curso | Es **normal**: hay materias comunes entre niveles. El importador no lo marca como error. |
| Materias cursando | Desde `cursos.csv`, con el alumno verificado. |

## Estructura real de cada archivo

### `cursos.csv`: materias por alumno (exportación completa)

Columnas: `codigo_alumno, apellido, nombre, inscripcion_id, periodo_alumno, nivel_inscripcion,
numero_curso, periodo_curso, curso_activo, seccion, materia_id, materia, dia_clase, profesor_id,
docente, carrera, centro, sede, modalidad, turno, nivel_curso, hora_inicio, hora_fin, fecha_inicio,
fecha_fin`.

Estadísticas del archivo recibido:

| Dato | Valor |
|---|---|
| Filas | 21.975 |
| Alumnos distintos | 3.002 |
| Inscripciones distintas | 3.089 (76 alumnos tienen más de una) |
| Carreras / materias distintas | 54 / 376 |
| Centros | ITS, ISICS, CPS, IFD (16 sedes) |
| Período | solo 2026, todos los cursos activos |
| Filas duplicadas exactas | **279**: el importador las descarta |
| `dia_clase` | vacío en todas las filas: el bot no puede informar días de clase |
| `nivel_inscripcion` distinto de `nivel_curso` | 3.711 filas: normal, son materias comunes entre niveles |

Lo que el bot podrá responder con este archivo: materias que cursa, carrera, sede, modalidad, turno,
docente, horario (`hora_inicio`-`hora_fin`) y fechas de inicio y fin de cada materia.

Este archivo trae carrera, sede, modalidad y turno **con nombre, pero sin sus IDs**. Por eso no
sirve para traducir los IDs de `aranceles.csv`: hacen falta los catálogos (ver pendientes).

### `alumno.csv`: datos del alumno (muestra de 10 filas)

Tiene 94 columnas, incluidos datos de padres, encargados, dirección, RUC y sincronización con
Moodle. **El CRM importará solo estas**:

| Columna | Uso |
|---|---|
| `codigo_alumno` | **Es el número de CI** (confirmado el 2026-10-13). Clave para unir con `cursos.csv` y dato de verificación. Se normaliza quitando puntos y espacios. |
| `apellido`, `nombre` | Saludo y ficha del alumno. |
| `fecha_nacimiento` | Segundo dato de verificación. |
| `telefono`, `telefono2`, `contacto_particular` | Comparar con el número de WhatsApp. |
| `email` | Envío de código de verificación. |
| `activo`, `fechaInactivo` | Estado del alumno. |

El resto de las columnas (padres, encargados, direcciones, RUC, Moodle) **no se importa**: el CRM
no las necesita, y no guardarlas reduce el riesgo.

Observaciones de la muestra:
- Son los registros **más antiguos** (códigos de 1–2 dígitos, 8 de 10 inactivos) y solo 1 de los 10
  aparece en `cursos.csv`, así que **no sirve para medir** cuántos alumnos actuales tienen celular o
  correo.
- Teléfonos en formatos mixtos: fijos de 6 dígitos sin prefijo, celulares con espacios y vacíos.
  Los correos estaban vacíos en las 10 filas.
- `activo = False` significa alumno inactivo **o con deuda** (confirmado). Por eso un alumno puede
  tener materias en `cursos.csv` y figurar inactivo.

### `aranceles.csv`: aranceles (muestra de 10 filas)

Columnas: `id, periodo, monto, nivel, moneda, activo, creado_el, modificado_el, carrera_id,
centro_id, concepto_id, creado_por_id, modalidad_id, modificado_por_id, sede_id, turno_id,
tipo_sede_id`.

- Carrera, centro, concepto, modalidad, sede, turno y tipo de sede vienen **solo como IDs**. Para
  que el bot diga "Técnico Superior en Farmacia, cuota: Gs. 200.000" hacen falta los **nombres**.
- `sede_id` y `turno_id` están vacíos en la muestra: el arancel parece depender de
  carrera + centro + modalidad + tipo de sede.
- Hay un monto de `2.00` (id 14115), probablemente un registro de prueba: el importador marcará como
  sospechoso cualquier monto menor a Gs. 1.000.

## Verificación de identidad (propuesta, a confirmar)

En el MVP, el único dato personal que muestra el bot son las **materias y horarios**. El estado de
cuenta va al portal o a Cobranzas. Propuesta:

1. **Celular registrado = número de WhatsApp** + CI (`codigo_alumno`) correcta → verificado.
2. Si el celular no coincide o no está cargado: CI + **fecha de nacimiento** → verificado solo para
   consultar materias.
3. Si tampoco coincide → ticket "verificación de identidad" para un funcionario.
4. El código por correo queda como opción futura, solo si la cobertura de correos es buena.

El bot nunca confirma si una CI existe. Después de 3 intentos fallidos, deriva a un humano.

## Uso de `activo` en el bot

- Un alumno inactivo **puede** verificarse y consultar sus materias: `activo` no bloquea la atención.
- El bot **no** dice "tiene deuda": `activo = False` no distingue entre deuda e inactividad, y el
  dato puede tener hasta un mes de antigüedad.
- Si el alumno inactivo consulta por acceso a la plataforma (caso "Habilitar plataforma" del manual
  de atención), el bot responde que su usuario figura inactivo, le indica revisar su estado de
  cuenta en el portal y crea un **ticket para Cobranzas** para que lo revisen y lo activen si
  corresponde.

## Pendientes para el próximo paso

1. **Catálogos con nombres** para los IDs de `aranceles.csv`, como CSV `id,nombre` de: carreras,
   conceptos, centros, modalidades, tipos de sede (y sedes y turnos, si se usan).
2. Opcional, pero recomendado: ejecutar el diagnóstico sobre el **`alumno.csv` completo** y pasar
   **solo la salida** (son cantidades, sin datos personales). Muestra cuántos alumnos tienen celular
   cargado, y con eso se sabe cuántos podrán verificarse automáticamente:
   ```bash
   python3 scripts/diagnostico_csv.py --alumnos alumno.csv --cursos cursos.csv --aranceles aranceles.csv
   ```

## Datos de prueba

`tests/datos_ficticios/` tiene los tres CSV con los **mismos encabezados reales** y datos inventados
(incluye a propósito una fila duplicada y un monto de prueba), para desarrollar y probar el
importador sin usar datos reales.

## Manejo de los archivos reales

- No se suben al repositorio: el `.gitignore` bloquea `*.csv`, salvo los ficticios.
- La exportación de `alumno.csv` incluye datos de padres y encargados que el CRM no usa. Si es
  posible, conviene exportar **solo las columnas listadas arriba**.
- En el servidor del CRM: carpeta con acceso restringido, importar y borrar.
