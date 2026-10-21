"""Marca los hallazgos sobre el documento: resaltado y comentario en el Word, o un reporte HTML.

En el Word, cada hallazgo con ubicación queda resaltado (rojo claro si la regla es dura, amarillo si es
blanda) y lleva un comentario con la regla y cómo corregirla. El texto no se modifica.
"""

import copy
import html
from pathlib import Path

from docx.enum.text import WD_COLOR_INDEX

COLOR = {"dura": WD_COLOR_INDEX.PINK, "blanda": WD_COLOR_INDEX.YELLOW}


def _tramos(resultado):
    """Agrupa las ubicaciones por párrafo, sin solapes. Si dos se pisan, gana la dura."""
    por_parrafo = {}
    for h in sorted(resultado.hallazgos, key=lambda h: h.severidad != "dura"):
        for u in h.ubicaciones:
            lista = por_parrafo.setdefault(u.ref, [])
            if any(u.inicio < z and a < u.fin for a, z, _ in lista):
                continue
            lista.append((u.inicio, u.fin, h))
    return por_parrafo


def _partir_run(run, corte):
    """Parte un run en dos en la posición `corte` y devuelve el segundo, con el mismo formato."""
    texto = run.text
    nuevo = copy.deepcopy(run._r)
    run._r.addnext(nuevo)
    from docx.text.run import Run

    segundo = Run(nuevo, run._parent)
    run.text = texto[:corte]
    segundo.text = texto[corte:]
    return segundo


def _runs_del_tramo(parrafo, inicio, fin):
    """Deja runs que empiezan y terminan exactamente en [inicio, fin) y los devuelve."""
    pos = 0
    for run in list(parrafo.runs):
        largo = len(run.text)
        if pos < inicio < pos + largo:
            run = _partir_run(run, inicio - pos)
            pos = inicio
            largo = len(run.text)
        if pos < fin < pos + largo:
            _partir_run(run, fin - pos)
            largo = len(run.text)
        pos += largo
    pos, dentro = 0, []
    for run in parrafo.runs:
        largo = len(run.text)
        if pos >= inicio and pos + largo <= fin and largo:
            dentro.append(run)
        pos += largo
    return dentro


def marcar_docx(origen, destino, resultado, autor="Humanizador"):
    import docx

    doc = docx.Document(str(origen))
    parrafos = doc.paragraphs
    n = 0
    for ref, tramos in _tramos(resultado).items():
        p = parrafos[ref]
        if "".join(r.text for r in p.runs) != p.text:
            continue  # párrafo con campos o hipervínculos: no se toca para no romperlo
        for inicio, fin, h in sorted(tramos, key=lambda t: -t[0]):
            runs = _runs_del_tramo(p, inicio, fin)
            if not runs:
                continue
            for r in runs:
                r.font.highlight_color = COLOR[h.severidad]
            etiqueta = "REGLA DURA" if h.severidad == "dura" else "Revisar"
            doc.add_comment(runs, text=f"{etiqueta}: {h.descripcion}. {h.como_corregir}.", author=autor,
                            initials="HZ")
            n += 1
    doc.save(str(destino))
    return n


def reporte_html(bloques, resultado, titulo="Revisión de redacción"):
    tramos = _tramos(resultado)
    cuerpo = []
    for b in bloques:
        t, partes, pos = b.texto, [], 0
        for inicio, fin, h in sorted(tramos.get(b.ref, []), key=lambda x: x[0]):
            partes.append(html.escape(t[pos:inicio]))
            clase = "dura" if h.severidad == "dura" else "blanda"
            partes.append(f'<mark class="{clase}" title="{html.escape(h.descripcion)}. '
                          f'{html.escape(h.como_corregir)}">{html.escape(t[inicio:fin])}</mark>')
            pos = fin
        partes.append(html.escape(t[pos:]))
        cuerpo.append(f"<p>{''.join(partes)}</p>")
    filas = "".join(
        f'<tr class="{h.severidad}"><td>{"Dura" if h.severidad == "dura" else "Blanda"}</td>'
        f"<td>{html.escape(h.descripcion)}</td><td>{html.escape(h.mensaje)}</td>"
        f"<td>{html.escape(h.como_corregir)}</td></tr>" for h in resultado.hallazgos)
    m = resultado.metricas
    estado = "Pasa las reglas duras" if resultado.pasa else "Falla en reglas duras"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title>
<style>
:root {{ --fondo:#fbfbf9; --tinta:#1d1d1b; --suave:#6b6b66; --linea:#e4e2dc; --dura:#ffc9c9; --blanda:#fff1a8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fondo:#191917; --tinta:#efeee9; --suave:#a3a29b; --linea:#34332f;
  --dura:#7a2f2f; --blanda:#6b5a12; }} }}
body {{ background:var(--fondo); color:var(--tinta); font:17px/1.65 Georgia, serif; margin:0; padding:24px 16px; }}
main {{ max-width:760px; margin:0 auto; }}
h1 {{ font:600 22px/1.3 system-ui, sans-serif; margin:0 0 4px; }}
.estado {{ font:15px system-ui, sans-serif; color:var(--suave); margin-bottom:24px; }}
table {{ width:100%; border-collapse:collapse; font:14px/1.4 system-ui, sans-serif; margin-bottom:32px; }}
td, th {{ border-bottom:1px solid var(--linea); padding:8px 6px; text-align:left; vertical-align:top; }}
mark {{ border-radius:3px; padding:0 2px; color:inherit; }}
mark.dura {{ background:var(--dura); }} mark.blanda {{ background:var(--blanda); }}
p {{ margin:0 0 1em; }}
</style></head><body><main>
<h1>{html.escape(titulo)}</h1>
<div class="estado">{estado} · perfil {html.escape(resultado.perfil)} · {m['palabras']} palabras ·
{len(resultado.duras)} reglas duras y {len(resultado.blandas)} señales para revisar</div>
<table><tr><th>Tipo</th><th>Regla</th><th>Medición</th><th>Cómo corregir</th></tr>{filas}</table>
{''.join(cuerpo)}
</main></body></html>"""


def guardar_html(bloques, resultado, destino, titulo=None):
    Path(destino).write_text(reporte_html(bloques, resultado, titulo or Path(destino).stem), encoding="utf-8")
