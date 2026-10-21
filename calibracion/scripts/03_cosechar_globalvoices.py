"""Cosecha posts de Global Voices en español (2016-2021) como lado HUMANO del perfil redes.

Global Voices publica con licencia Creative Commons Atribución 3.0. Muchos posts en español son traducciones
del inglés: se guardan solo los que dicen "Escrito por" sin idioma de origen y sin traductor, es decir, los
escritos originalmente en español. Se descartan citas en bloque y leyendas de imágenes.

Uso: python 03_cosechar_globalvoices.py 300
Salida: datos/globalvoices_humano.jsonl
"""

import html as htmlmod
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATOS = Path(__file__).resolve().parents[1] / "datos"
SALIDA = DATOS / "globalvoices_humano.jsonl"
OBJETIVO = int(sys.argv[1]) if len(sys.argv) > 1 else 300
UA = {"User-Agent": "Mozilla/5.0 (investigacion academica; calibracion de estilo)"}


def bajar(url):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            time.sleep(3 * (k + 1))
    return ""


def enlaces_del_mes(anio, mes):
    vistos = []
    for pagina in (1, 2, 3):
        url = f"https://es.globalvoices.org/{anio}/{mes:02d}/" + (f"page/{pagina}/" if pagina > 1 else "")
        t = bajar(url)
        nuevos = re.findall(rf"https://es\.globalvoices\.org/{anio}/{mes:02d}/\d\d/[^\"#?\s']+/", t)
        nuevos = [u for u in dict.fromkeys(nuevos) if "/page/" not in u and u not in vistos]
        if not nuevos:
            break
        vistos += nuevos
    return vistos


def post(url):
    t = bajar(url)
    if not t:
        return None
    etiquetas = set(re.findall(r"credit-label'>([^<]+)<", t))
    # la plantilla siempre trae "Escrito por" y "Traducido por"; una traducción se delata con el idioma de
    # origen entre paréntesis ("Escrito (English) por", "Traducido (Español) por")
    if any(e.startswith(("Escrito (", "Traducido (")) for e in etiquetas):
        return None
    if "creativecommons.org/licenses/by/3.0" not in t:
        return None
    sin_citas = re.sub(r"<blockquote.*?</blockquote>", " ", t, flags=re.S)
    pars = []
    for m in re.finditer(r"<p>(.*?)</p>", sin_citas, flags=re.S):
        p = htmlmod.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        p = re.sub(r"\s+", " ", p).strip()
        if len(p.split()) >= 15 and not p.startswith(("Apoya el periodismo", "Este artículo", "Este post")):
            pars.append(p)
    if sum(len(p.split()) for p in pars) < 200:
        return None
    titulo = re.search(r'<meta property="og:title" content="([^"]+)"', t)
    autor = re.search(r"credit-label'>Escrito por</span><a[^>]*>([^<]+)<", t)
    fecha = re.search(r"es\.globalvoices\.org/(\d{4})/(\d\d)/", url)
    return {"pid": url.rstrip("/").rsplit("/", 1)[-1][:80], "url": url, "anio": fecha.group(1),
            "titulo": htmlmod.unescape(titulo.group(1)) if titulo else "", "autor": autor.group(1) if autor else "",
            "licencia": "CC BY 3.0", "parrafos": pars}


def main():
    hechos = set()
    if SALIDA.exists():
        hechos = {json.loads(l)["url"] for l in SALIDA.read_text(encoding="utf-8").splitlines()}
    n = len(hechos)
    meses = [(a, m) for a in range(2016, 2022) for m in range(1, 13)]
    with SALIDA.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=4) as ex:
        for anio, mes in meses:
            if n >= OBJETIVO:
                break
            urls = [u for u in enlaces_del_mes(anio, mes) if u not in hechos]
            tomados = 0
            for r in ex.map(post, urls):
                if r and n < OBJETIVO and tomados < 8:  # pocos por mes, para repartir en el tiempo y entre autores
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    f.flush()
                    n += 1
                    tomados += 1
            print(anio, mes, "enlaces", len(urls), "tomados", tomados, "total", n, flush=True)
    print("TOTAL", n)


if __name__ == "__main__":
    main()
