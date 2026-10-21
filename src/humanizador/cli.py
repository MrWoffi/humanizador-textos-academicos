"""Línea de comandos: humanizador archivo [--perfil academico] [--marcar] [--html] [--json]."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .lector import leer
from .reglas import perfiles_disponibles, revisar


def imprimir(r, max_ejemplos=6):
    m = r.metricas
    print(f"Perfil: {r.perfil} | {m['palabras']} palabras en {m['parrafos']} párrafos de prosa")
    claves = [k for k in m if k not in ("palabras", "parrafos")]
    print("Métricas: " + ", ".join(f"{k}={m[k]}" for k in claves))
    for titulo, lista in (("REGLAS DURAS", r.duras), ("SEÑALES PARA REVISAR", r.blandas)):
        print(f"\n== {titulo}: " + ("ninguna" if not lista else f"{len(lista)}"))
        for h in lista:
            print(f"- {h.descripcion}: {h.mensaje}")
            print(f"    Cómo corregir: {h.como_corregir}")
            for u in h.ubicaciones[:max_ejemplos]:
                print(f"    · {u.extracto}")
            if len(h.ubicaciones) > max_ejemplos:
                print(f"    · … y {len(h.ubicaciones) - max_ejemplos} más")
    if r.n_senales:
        n, cal = len(r.senales), r.calibracion
        print(f"\nSeñales calibradas: {n} de {r.n_senales}" + (f" ({', '.join(r.senales)})" if n else ""))
        if cal:
            print(f"    En la calibración, {cal['corte']} o más aparecieron en el {cal['ia']:.0%} de los textos de IA "
                  f"y en el {cal['humanos']:.0%} de los humanos ({cal['corpus']}).")
    print("\nVeredicto:", "PASA las reglas duras" if r.pasa else "FALLA en reglas duras",
          "(revisa las señales con criterio, no son mandamientos)" if r.blandas else "")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="humanizador",
        description="Mide la huella de IA en textos en español. Mide, no reescribe.")
    ap.add_argument("archivo", help=".docx, .md, .txt o .html")
    ap.add_argument("--perfil", default="academico",
                    help=f"{', '.join(perfiles_disponibles())} o la ruta a un .toml propio (defecto: academico)")
    ap.add_argument("--marcar", action="store_true",
                    help="en un .docx, guarda una copia con los hallazgos resaltados y comentados")
    ap.add_argument("--html", action="store_true", help="guarda un reporte HTML con el texto marcado")
    ap.add_argument("--json", action="store_true", help="imprime el resultado en JSON")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = ap.parse_args(argv)

    ruta = Path(a.archivo)
    if not ruta.exists():
        ap.error(f"no existe {ruta}")
    bloques = leer(ruta)
    if not bloques:
        print("No se encontró prosa que revisar.", file=sys.stderr)
        return 2
    r = revisar(bloques, a.perfil)

    if a.json:
        print(json.dumps(r.a_dict(), ensure_ascii=False, indent=2))
    else:
        imprimir(r)
    if a.marcar:
        if ruta.suffix.lower() != ".docx":
            print("\n--marcar solo funciona con .docx. Usa --html para otros formatos.", file=sys.stderr)
        else:
            from .marcar import marcar_docx

            destino = ruta.with_name(f"{ruta.stem} (revisado).docx")
            n = marcar_docx(ruta, destino, r)
            print(f"\nCopia marcada con {n} comentarios: {destino}")
    if a.html:
        from .marcar import guardar_html

        destino = ruta.with_name(f"{ruta.stem} (revisión).html")
        guardar_html(bloques, r, destino, titulo=f"Revisión de {ruta.name}")
        print(f"Reporte HTML: {destino}")
    return 0 if r.pasa else 1


if __name__ == "__main__":
    sys.exit(main())
