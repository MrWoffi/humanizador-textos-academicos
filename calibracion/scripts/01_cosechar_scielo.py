"""Cosecha introducciones de articulos de SciELO en espanol (2015-2020) como lado HUMANO academico.

Solo guarda articulos cuyo idioma principal es espanol, con texto completo HTML en espanol y una licencia
Creative Commons detectada en la propia pagina. Guarda tambien el titulo, que sirve de consigna para el
lado IA (corpus pareado, como StoryScope).

Salida: datos/scielo_humano.jsonl
"""

import html as htmlmod
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "datos"
SALIDA = BASE / "scielo_humano.jsonl"
OBJETIVO = int(sys.argv[1]) if len(sys.argv) > 1 else 260

REVISTAS = [  # (coleccion, issn, dominio web)
    ("col", "0121-4772", "www.scielo.org.co"), ("col", "0120-2596", "www.scielo.org.co"),
    ("col", "0120-3584", "www.scielo.org.co"), ("col", "0120-6346", "www.scielo.org.co"),
    ("col", "0121-5051", "www.scielo.org.co"), ("col", "0120-3592", "www.scielo.org.co"),
    ("per", "0252-1865", "www.scielo.org.pe"), ("per", "0254-4415", "www.scielo.org.pe"),
    ("mex", "0185-1667", "www.scielo.org.mx"), ("mex", "0186-1042", "www.scielo.org.mx"),
    ("chl", "0717-6821", "www.scielo.cl"), ("arg", "1851-3727", "www.scielo.org.ar"),
]
UA = {"User-Agent": "Mozilla/5.0 (investigacion academica; calibracion de estilo)"}


def get(url, intentos=3):
    for k in range(intentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception:
            time.sleep(2 + 3 * k)
    return None


def parrafos(h):
    ps = re.findall(r"<p[^>]*>(.*?)</p>", h, re.S | re.I)
    out = []
    for p in ps:
        t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", p))
        t = re.sub(r"\s+", " ", t).strip()
        out.append(t)
    return out


def introduccion(ps):
    """Parrafos de cuerpo desde 'Introduccion' (o desde el primer parrafo largo tras el resumen)."""
    ini = None
    for i, t in enumerate(ps):
        if re.match(r"^(\d\.?\s*|I\.?\s*)?introducci[oó]n\.?$", t.strip(), re.I):
            ini = i + 1
            break
    if ini is None:
        return []
    cuerpo = []
    for t in ps[ini:]:
        if re.match(r"^(\d|II|2)[\.\s]", t) and len(t.split()) < 15:
            break  # siguiente seccion
        if len(t.split()) >= 25:
            cuerpo.append(t)
        if sum(len(c.split()) for c in cuerpo) >= 600:
            break
    return cuerpo


def main():
    vistos = set()
    if SALIDA.exists():
        for l in SALIDA.read_text(encoding="utf-8").splitlines():
            vistos.add(json.loads(l)["pid"])
    n = len(vistos)
    with SALIDA.open("a", encoding="utf-8") as f:
        for col, issn, dom in REVISTAS:
            ids = get(f"https://articlemeta.scielo.org/api/v1/article/identifiers/?collection={col}&issn={issn}"
                      f"&from=2015-01-01&until=2020-12-31&limit=400")
            if not ids:
                print("sin indice", issn); continue
            objs = json.loads(ids)["objects"]
            tomados = 0
            motivo = {}
            for o in objs:
                if n >= OBJETIVO or tomados >= 40:
                    break
                pid = o["code"]
                if pid in vistos:
                    continue
                meta = get(f"https://articlemeta.scielo.org/api/v1/article/?code={pid}&collection={col}")
                if not meta:
                    continue
                m = json.loads(meta)
                lang = (m.get("article", {}).get("v40") or [{}])[0].get("_")
                url = ((m.get("fulltexts") or {}).get("html") or {}).get("es")
                anio = m.get("publication_year")
                if lang != "es" or not url or not anio or not ("2015" <= anio <= "2020"):
                    motivo["meta"] = motivo.get("meta", 0) + 1
                    continue
                raw = get(url)
                if not raw:
                    continue
                h = raw.decode("utf-8", errors="replace") if b"charset=utf-8" in raw[:3000].lower() \
                    else raw.decode("latin-1", errors="replace")
                lic = re.search(r"creativecommons\.org/licenses/([a-z\-]+)/(\d\.\d)", h)
                if not lic:
                    motivo["licencia"] = motivo.get("licencia", 0) + 1
                    continue
                cuerpo = introduccion(parrafos(h))
                if sum(len(c.split()) for c in cuerpo) < 120 or len(cuerpo) < 2:
                    motivo["intro"] = motivo.get("intro", 0) + 1
                    continue
                titulos = m.get("article", {}).get("v12") or []
                titulo = next((t["_"] for t in titulos if t.get("l") == "es"), None)
                if not titulo:
                    continue
                f.write(json.dumps({"pid": pid, "coleccion": col, "issn": issn, "anio": anio, "url": url,
                                    "licencia": f"CC {lic.group(1).upper()} {lic.group(2)}",
                                    "titulo": titulo, "parrafos": cuerpo}, ensure_ascii=False) + "\n")
                f.flush()
                vistos.add(pid); n += 1; tomados += 1
                time.sleep(0.4)
            print(issn, "objetos", len(objs), "tomados", tomados, "total", n, motivo, flush=True)
    print("TOTAL", n)


if __name__ == "__main__":
    main()
