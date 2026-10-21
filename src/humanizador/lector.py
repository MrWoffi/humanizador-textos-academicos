"""Lee un documento y lo parte en bloques de prosa.

Cada bloque recuerda de qué párrafo del original salió (`ref`), para poder marcar los hallazgos en el
mismo lugar. Se saltan títulos, leyendas de figuras y tablas, notas, ecuaciones y todo lo que viene
después de las referencias.
"""

import re
from dataclasses import dataclass
from pathlib import Path

LEYENDA = re.compile(r"^(Figura|Tabla|Gráfico|Cuadro|Nota\.|Fuente:|Elaboración propia|Salida de |Anexo [A-Z]\b)", re.I)
FIN_PROSA = re.compile(r"^(Referencias|Referencias bibliográficas|Bibliografía|References|Anexos?)\s*$", re.I)
ABREVIATURAS = ("et al", "cap", "caps", "p", "pp", "dic", "ed", "eds", "vol", "núm", "n", "vs", "sr", "sra", "dr",
                "dra", "ej", "etc", "aprox", "fig", "art", "inc", "ca", "op", "cit", "ibid", "ss", "trad", "N.º")


@dataclass
class Bloque:
    texto: str
    ref: int  # índice del párrafo en el documento original (docx) o del bloque (texto)


def leer(ruta):
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    if ext == ".docx":
        return _leer_docx(ruta)
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    if ext in (".html", ".htm"):
        texto = _html_a_texto(texto)
    elif ext in (".md", ".markdown"):
        texto = _limpiar_md(texto)
    return _bloques_de_texto(texto)


def _leer_docx(ruta):
    import docx

    d = docx.Document(str(ruta))
    bloques = []
    for i, p in enumerate(d.paragraphs):
        t = p.text.strip()
        estilo = (p.style.name or "").lower() if p.style is not None else ""
        if FIN_PROSA.match(t):
            break
        if t and "heading" not in estilo and "título" not in estilo and "title" not in estilo:
            bloques.append(Bloque(p.text, i))
    return [b for b in bloques if es_prosa(b.texto)]


def _html_a_texto(texto):
    texto = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", texto, flags=re.S | re.I)
    texto = re.sub(r"<h\d[^>]*>.*?</h\d>", "\n\n", texto, flags=re.S | re.I)
    texto = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</td>", "\n\n", texto, flags=re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"&nbsp;", " ", texto)


def _limpiar_md(texto):
    texto = re.sub(r"```.*?```", " ", texto, flags=re.S)
    texto = re.sub(r"\A---\n.*?\n---\n", "", texto, flags=re.S)
    # cada ítem de lista es un bloque propio, aunque no haya línea en blanco entre ítems
    texto = re.sub(r"\n(?=\s*(?:[-*+]|\d+\.)\s)", "\n\n", texto)
    salida = []
    for b in re.split(r"\n\s*\n", texto):
        b = b.strip()
        if FIN_PROSA.match(re.sub(r"^#+\s*", "", b)):
            salida.append("\x00FIN")
            break
        if b.startswith("#") or b.startswith("|") or b.startswith(">"):
            continue
        b = re.sub(r"^(?:[-*+]|\d+\.)\s+", "", b)
        b = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", b)
        b = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", b)
        b = re.sub(r"(\*\*|__|\*|_|`)", "", b)
        salida.append(b)
    return "\n\n".join(salida)


def _bloques_de_texto(texto):
    bloques = []
    for i, b in enumerate(re.split(r"\n\s*\n", texto)):
        if b.strip() == "\x00FIN" or FIN_PROSA.match(b.strip()):
            break
        b = " ".join(l.strip() for l in b.splitlines()).strip()
        if es_prosa(b):
            bloques.append(Bloque(b, i))
    return bloques


def es_prosa(t):
    t = t.strip()
    if len(t) < 40 or LEYENDA.match(t):
        return False
    simbolos = sum(t.count(c) for c in "=Σ+−^")
    return simbolos < 3 or len(t.split()) > 25


def frases(texto):
    """Parte un bloque en frases con su posición (inicio, fin) dentro del bloque."""
    cortes = [0]
    for m in re.finditer(r"[.!?…]+[\"”»)]?\s+(?=[¿¡«\"“(A-ZÁÉÍÓÚÑ0-9])", texto):
        previo = texto[:m.start()].rsplit(None, 1)
        ultima = previo[-1].lower().rstrip(".") if previo else ""
        if ultima in ABREVIATURAS or re.fullmatch(r"[a-záéíóú]", ultima):
            continue
        cortes.append(m.end())
    cortes.append(len(texto))
    salida = []
    for a, b in zip(cortes, cortes[1:]):
        f = texto[a:b].strip()
        if len(f.split()) >= 3:
            ini = texto.index(f, a)
            salida.append((f, ini, ini + len(f)))
    return salida
