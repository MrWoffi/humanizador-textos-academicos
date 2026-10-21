"""Genera el lado IA del corpus pareado: una introduccion por cada titulo humano de SciELO.

Consigna neutra, sin pedir ni prohibir estilo, para obtener la salida por defecto del modelo.
Modelos alternados: deepseek-v4.1-flash (NVIDIA NIM) y gemini-flash-latest (Google AI Studio).
Las claves se leen de las variables de entorno de usuario; nunca se escriben en disco.

Salida: datos/ia_generado.jsonl
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "datos"
HUMANO = BASE / "scielo_humano.jsonl"
SALIDA = BASE / "ia_generado.jsonl"
LIMITE = int(sys.argv[1]) if len(sys.argv) > 1 else 10**6

CONSIGNA = ("Escribe la introducción de un artículo académico de economía titulado «{t}». "
            "Entre 350 y 550 palabras, en párrafos. Devuelve solo el texto de la introducción, sin título.")


def clave(nombre):
    v = os.environ.get(nombre)
    if v:
        return v.strip()
    return subprocess.run(["powershell", "-NoProfile", "-Command",
                           f"[Environment]::GetEnvironmentVariable('{nombre}','User')"],
                          capture_output=True, text=True).stdout.strip()


NIM = clave("NVIDIA_API_KEY_2")
GEM = clave("GOOGLE_API_KEY")


def post(url, cuerpo, cabeceras):
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), headers=cabeceras, method="POST")
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())


def deepseek(texto):
    d = post("https://integrate.api.nvidia.com/v1/chat/completions",
             {"model": "deepseek-ai/deepseek-v4.1-flash", "messages": [{"role": "user", "content": texto}],
              "max_tokens": 8000, "temperature": 0.7},
             {"Authorization": f"Bearer {NIM}", "Content-Type": "application/json"})
    c = d["choices"][0]["message"].get("content")
    if not c:
        raise RuntimeError("deepseek sin contenido")
    return c


def gemini(texto):
    d = post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEM}",
             {"contents": [{"parts": [{"text": texto}]}], "generationConfig": {"temperature": 0.7}},
             {"Content-Type": "application/json"})
    return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])


MODELOS = [("deepseek-v4.1-flash", deepseek), ("gemini-flash-latest", gemini)]


def limpiar(t):
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    t = re.sub(r"^\s*#+.*$", "", t, flags=re.M)        # titulos markdown
    t = re.sub(r"^\s*\*\*?Introducci[oó]n\*\*?\s*$", "", t, flags=re.M | re.I)
    t = t.replace("**", "").replace("*", "")   # enfasis markdown
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t) if len(p.split()) >= 15]


def una(i, h):
    nombre, fn = MODELOS[0] if i % 3 == 0 else MODELOS[1]
    for k in range(5):
        try:
            pars = limpiar(fn(CONSIGNA.format(t=h["titulo"])))
            break
        except Exception as e:
            print("reintento", nombre, k, str(e)[:120], flush=True)
            time.sleep(15 * (k + 1))
    else:
        return None
    if sum(len(p.split()) for p in pars) < 120:
        return None
    return {"pid": h["pid"], "modelo": nombre, "titulo": h["titulo"], "parrafos": pars}


def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    hechos = set()
    if SALIDA.exists():
        hechos = {json.loads(l)["pid"] for l in SALIDA.read_text(encoding="utf-8").splitlines()}
    humanos = [json.loads(l) for l in HUMANO.read_text(encoding="utf-8").splitlines()]
    tareas = [(i, h) for i, h in enumerate(humanos) if h["pid"] not in hechos][:LIMITE]
    candado = threading.Lock()
    n = 0
    with SALIDA.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(una, i, h) for i, h in tareas]
        for fu in as_completed(futs):
            r = fu.result()
            if not r:
                continue
            with candado:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
                n += 1
            print(n, r["modelo"], sum(len(p.split()) for p in r["parrafos"]), "palabras", flush=True)
    print("TOTAL", n)


if __name__ == "__main__":
    main()
