"""Genera el lado IA con un modelo dado, sobre los títulos del lado humano (corpus pareado).

Uso:
  python 04_generar_modelos.py academico claude-sonnet 100
  python 04_generar_modelos.py redes gpt-oss-20b 100

Modelos:
  claude-sonnet   Claude Sonnet por la CLI de Claude Code, sin CLAUDE.md ni ajustes del usuario
                  (--setting-sources "") y con un system prompt neutro, para que no herede reglas de estilo.
  gpt-oss-20b     modelo abierto de OpenAI, por NVIDIA NIM (variable NVIDIA_API_KEY_2)
  gemini          gemini-flash-latest, por Google AI Studio (variable GOOGLE_API_KEY)
  deepseek        deepseek-v4.1-flash, por NVIDIA NIM (variable NVIDIA_API_KEY_2)

Las claves se leen de variables de entorno y nunca se escriben en disco. El texto se guarda en datos/, que no
se publica.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DATOS = Path(__file__).resolve().parents[1] / "datos"
CORPUS = {
    "academico": ("scielo_humano.jsonl", "ia_generado.jsonl",
                  "Escribe la introducción de un artículo académico de economía titulado «{t}». Entre 350 y 550 "
                  "palabras, en párrafos. Devuelve solo el texto de la introducción, sin título."),
    "redes": ("globalvoices_humano.jsonl", "ia_redes.jsonl",
              "Escribe un artículo para un blog sobre «{t}». Entre 350 y 550 palabras, en párrafos. Devuelve solo "
              "el texto del artículo, sin título."),
}


def clave(nombre):
    v = os.environ.get(nombre)
    if v:
        return v.strip()
    return subprocess.run(["powershell", "-NoProfile", "-Command",
                           f"[Environment]::GetEnvironmentVariable('{nombre}','User')"],
                          capture_output=True, text=True).stdout.strip()


def post(url, cuerpo, cabeceras):
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), headers=cabeceras, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def nim(modelo):
    k = clave("NVIDIA_API_KEY_2")

    def llamar(texto):
        d = post("https://integrate.api.nvidia.com/v1/chat/completions",
                 {"model": modelo, "messages": [{"role": "user", "content": texto}], "max_tokens": 8000,
                  "temperature": 0.7},
                 {"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
        c = d["choices"][0]["message"].get("content")
        if not c:
            raise RuntimeError("respuesta sin contenido")
        return c
    return llamar


def gemini():
    k = clave("GOOGLE_API_KEY")

    def llamar(texto):
        d = post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={k}",
                 {"contents": [{"parts": [{"text": texto}]}], "generationConfig": {"temperature": 0.7}},
                 {"Content-Type": "application/json"})
        return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    return llamar


def claude_cli(modelo="sonnet"):
    vacio = tempfile.mkdtemp(prefix="hz_")  # carpeta vacía: sin CLAUDE.md de proyecto

    def llamar(texto):
        # la consigna va por stdin: en Windows, claude es un .cmd y cmd.exe estropea comillas y acentos
        r = subprocess.run([shutil.which("claude"), "-p", "--setting-sources=", "--model", modelo,
                            "--system-prompt", "You are a helpful assistant.", "--output-format", "text"],
                           input=texto, capture_output=True, text=True, encoding="utf-8", cwd=vacio, timeout=400)
        if r.returncode != 0 or not r.stdout.strip():
            raise RuntimeError(f"claude -p falló: {r.stderr[:200]}")
        return r.stdout
    return llamar


MODELOS = {
    "claude-sonnet": lambda: claude_cli("sonnet"),
    "gpt-oss-20b": lambda: nim("openai/gpt-oss-20b"),
    "deepseek": lambda: nim("deepseek-ai/deepseek-v4.1-flash"),
    "gemini": gemini,
}
NOMBRE = {"claude-sonnet": "claude-sonnet", "gpt-oss-20b": "gpt-oss-20b", "deepseek": "deepseek-v4.1-flash",
          "gemini": "gemini-flash-latest"}


def limpiar(t):
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    t = re.sub(r"^\s*#+.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\*\*?(Introducci[oó]n|T[ií]tulo)[^\n]*$", "", t, flags=re.M | re.I)
    t = t.replace("**", "").replace("*", "")
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t) if len(p.split()) >= 15]


def main():
    corpus, modelo, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    hum, sal, consigna = CORPUS[corpus]
    salida = DATOS / sal
    nombre = NOMBRE[modelo]
    hechos = set()
    if salida.exists():
        hechos = {json.loads(l)["pid"] for l in salida.read_text(encoding="utf-8").splitlines()
                  if json.loads(l)["modelo"] == nombre}
    humanos = [json.loads(l) for l in (DATOS / hum).read_text(encoding="utf-8").splitlines()]
    ya_otros = {}
    if salida.exists():
        for l in salida.read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            ya_otros[r["pid"]] = ya_otros.get(r["pid"], 0) + 1
    # cada título lo escribe un solo modelo cuando se puede: se priorizan los que nadie escribió
    pendientes = sorted((h for h in humanos if h["pid"] not in hechos), key=lambda h: ya_otros.get(h["pid"], 0))
    tareas = pendientes[:max(0, n - len(hechos))]
    fn = MODELOS[modelo]()
    candado = threading.Lock()
    hechos_n = len(hechos)

    def una(h):
        for k in range(4):
            try:
                pars = limpiar(fn(consigna.format(t=h["titulo"])))
                if sum(len(p.split()) for p in pars) >= 200:
                    return {"pid": h["pid"], "modelo": nombre, "titulo": h["titulo"], "parrafos": pars}
            except Exception as e:  # noqa: BLE001
                print("reintento", k, str(e)[:150], flush=True)
                time.sleep(20 * (k + 1))
        return None

    workers = 3 if modelo == "claude-sonnet" else 5
    with salida.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        for fu in as_completed([ex.submit(una, h) for h in tareas]):
            r = fu.result()
            if r:
                with candado:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    f.flush()
                    hechos_n += 1
                print(hechos_n, nombre, sum(len(p.split()) for p in r["parrafos"]), "palabras", flush=True)
    print("TOTAL", nombre, hechos_n)


if __name__ == "__main__":
    main()
