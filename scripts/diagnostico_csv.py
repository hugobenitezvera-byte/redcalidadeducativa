#!/usr/bin/env python3
"""Diagnóstico de calidad de los CSV exportados del sistema académico.

Imprime SOLO conteos y porcentajes (ningún nombre, documento, teléfono ni correo),
para decidir cómo verificar la identidad de los alumnos por WhatsApp.

Uso (en la PC donde están los archivos; no hace falta subirlos a ningún lado):
  python3 scripts/diagnostico_csv.py --alumnos alumno.csv --cursos cursos.csv --aranceles aranceles.csv

Formato esperado: exportación de PostgreSQL con encabezados, separador coma,
valores nulos como NULL y booleanos como True/False.
"""
import argparse
import collections
import csv
import re
import sys

NULOS = {"", "NULL", "null", "None"}
# Celular paraguayo: 09XXXXXXXX, 9XXXXXXXX o 5959XXXXXXXX (con o sin espacios/guiones).
CELULAR_PY = re.compile(r"^(?:0?9\d{8}|5959\d{8})$")
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def leer(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        muestra = f.read(4096)
        f.seek(0)
        sep = ";" if muestra.count(";") > muestra.count(",") else ","
        return list(csv.DictReader(f, delimiter=sep))


def vacio(v):
    return v is None or v.strip() in NULOS


def es_celular(v):
    return not vacio(v) and bool(CELULAR_PY.match(re.sub(r"\D", "", v)))


def pct(n, total):
    return f"{n} ({100 * n / total:.1f}%)" if total else "0"


def requeridas(filas, columnas, nombre):
    faltan = [c for c in columnas if filas and c not in filas[0]]
    if faltan:
        sys.exit(f"{nombre}: faltan columnas {faltan}")


def diag_cursos(filas):
    requeridas(filas, ["codigo_alumno", "inscripcion_id", "materia", "carrera", "periodo_curso"], "cursos")
    print("== cursos")
    print("filas:", len(filas))
    print("filas duplicadas exactas:", len(filas) - len({tuple(r.values()) for r in filas}))
    print("alumnos distintos:", len({r["codigo_alumno"] for r in filas}))
    print("inscripciones distintas:", len({r["inscripcion_id"] for r in filas}))
    print("carreras distintas:", len({r["carrera"] for r in filas}))
    print("materias distintas:", len({r["materia"] for r in filas}))
    print("períodos:", dict(collections.Counter(r["periodo_curso"] for r in filas)))
    return {r["codigo_alumno"] for r in filas}


def diag_alumnos(filas, codigos_cursando):
    requeridas(filas, ["codigo_alumno", "telefono", "email", "fecha_nacimiento", "activo"], "alumnos")
    print("== alumnos")
    print("filas:", len(filas))
    codigos = [r["codigo_alumno"] for r in filas]
    print("codigo_alumno repetidos:", len(codigos) - len(set(codigos)))
    print("largo de codigo_alumno:", dict(sorted(collections.Counter(len(c) for c in codigos).items())))
    if "ruc" in filas[0]:
        print("codigo_alumno igual a ruc:", pct(sum(r["codigo_alumno"] == r["ruc"] for r in filas), len(filas)))

    grupos = [("todos", filas)]
    if codigos_cursando is not None:
        cursando = [r for r in filas if r["codigo_alumno"] in codigos_cursando]
        grupos.append(("con materias en cursos.csv", cursando))
        print("alumnos de cursos.csv que NO están en alumnos.csv:",
              len(codigos_cursando - set(codigos)))

    for nombre, g in grupos:
        n = len(g)
        cel = sum(any(es_celular(r.get(c)) for c in ("telefono", "telefono2", "contacto_particular")) for r in g)
        mail = sum(not vacio(r["email"]) and bool(CORREO.match(r["email"].strip())) for r in g)
        nac = sum(not vacio(r["fecha_nacimiento"]) for r in g)
        ninguno = sum(
            not any(es_celular(r.get(c)) for c in ("telefono", "telefono2", "contacto_particular"))
            and not (not vacio(r["email"]) and CORREO.match(r["email"].strip()))
            for r in g
        )
        print(f"-- {nombre}: {n} alumnos")
        print("   con celular válido:", pct(cel, n))
        print("   con correo válido:", pct(mail, n))
        print("   con fecha de nacimiento:", pct(nac, n))
        print("   sin celular ni correo:", pct(ninguno, n))
        print("   activo:", dict(collections.Counter(r["activo"] for r in g)))

    # Celulares compartidos por varios alumnos (p. ej. el de un familiar).
    por_cel = collections.Counter(
        re.sub(r"\D", "", r["telefono"])[-9:] for r in filas if es_celular(r["telefono"])
    )
    print("celulares usados por más de un alumno:", sum(1 for v in por_cel.values() if v > 1))


def diag_aranceles(filas):
    requeridas(filas, ["monto", "activo", "carrera_id", "concepto_id"], "aranceles")
    print("== aranceles")
    print("filas:", len(filas), "| activos:", sum(r["activo"] == "True" for r in filas))
    print("carreras (ids) distintas:", len({r["carrera_id"] for r in filas}))
    print("conceptos (ids):", dict(collections.Counter(r["concepto_id"] for r in filas)))
    sospechosos = [r["id"] for r in filas if not vacio(r["monto"]) and float(r["monto"]) < 1000]
    print("montos menores a 1.000 (posibles registros de prueba), ids:", sospechosos)
    ids = [c for c in filas[0] if c.endswith("_id") and c not in ("creado_por_id", "modificado_por_id")]
    print("columnas que necesitan catálogo con nombres:", ids)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alumnos")
    p.add_argument("--cursos")
    p.add_argument("--aranceles")
    a = p.parse_args()
    if not (a.alumnos or a.cursos or a.aranceles):
        p.error("indicar al menos un archivo")

    codigos = diag_cursos(leer(a.cursos)) if a.cursos else None
    if a.alumnos:
        diag_alumnos(leer(a.alumnos), codigos)
    if a.aranceles:
        diag_aranceles(leer(a.aranceles))


if __name__ == "__main__":
    main()
