"""Mide las métricas del humanizador sobre el lado humano y el lado IA de un corpus y propone umbrales.

Por métrica: medianas, AUC (probabilidad de que un texto de IA puntúe más alto que uno humano) y el umbral que
marca solo lo que un humano rara vez hace: percentil 90 humano si la IA puntúa más alto, percentil 10 humano si
puntúa más bajo. Una métrica "separa" si su AUC se aleja al menos 0.1 de 0.5.

Uso: python 05_medir.py academico|redes
Salida: resultado_<corpus>.json y metricas_por_texto_<corpus>.csv (sin texto, solo identificadores y cifras)
"""

import ast
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from humanizador.lector import Bloque, es_prosa  # noqa: E402
from humanizador.reglas import revisar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"  # los textos no se publican: se rearman con los scripts 01 a 04
CORPUS = {"academico": ("scielo_humano.jsonl", "ia_generado.jsonl"),
          "redes": ("globalvoices_humano.jsonl", "ia_redes.jsonl")}
NO_SON_SENALES = {"palabras", "parrafos", "frases"}


def cargar(nombre):
    salida = []
    for linea in (DATOS / nombre).read_text(encoding="utf-8").splitlines():
        r = json.loads(linea)
        pars = r["parrafos"] if isinstance(r["parrafos"], list) else ast.literal_eval(r["parrafos"])
        bloques = [Bloque(p, i) for i, p in enumerate(pars) if es_prosa(p)]
        if sum(len(b.texto.split()) for b in bloques) >= 200:
            salida.append((r, bloques))
    return salida


def metricas(bloques):
    m = revisar(bloques, "academico").metricas
    pal = m["palabras"]
    for k in [k for k in m if k.endswith("_n")]:
        m[k[:-2] + "_x1000"] = m.pop(k) * 1000 / pal
    return m


def auc(ia, hu):
    ia, hu = np.asarray(ia), np.asarray(hu)
    return float((ia[:, None] > hu[None, :]).mean() + (ia[:, None] == hu[None, :]).mean() / 2)


def umbral(h, op, tope=0.10, tope_relajado=0.20):
    """El umbral más exigente que marca como mucho al 10% de los humanos.

    Si con el 10% el umbral queda en el mínimo (pasa cuando la mayoría de los humanos tiene cero, como con las
    citas), se admite hasta el 20%. Si ni así marca a nadie, la métrica no sirve como señal en ese sentido.
    """
    h = np.asarray(h)
    valores = np.unique(h)
    for t in (tope, tope_relajado):
        if op == ">":
            validos = [v for v in valores if (h > v).mean() <= t]
            u = min(validos)
            if (h > u).mean() > 0 or u > 0:
                return round(float(u), 3)
        else:
            validos = [v for v in valores if (h < v).mean() <= t]
            u = max(validos)
            if (h < u).mean() > 0:
                return round(float(u), 3)
    return round(float(u), 3)


def marca(v, op, u):
    return v > u if op == ">" else v < u


def main():
    corpus = sys.argv[1]
    hum_f, ia_f = CORPUS[corpus]
    hum = [(r, metricas(b)) for r, b in cargar(hum_f)]
    ia = [(r, metricas(b)) for r, b in cargar(ia_f)]
    H, A = [m for _, m in hum], [m for _, m in ia]
    claves = [k for k in H[0] if k not in NO_SON_SENALES]
    filas = {}
    for k in claves:
        h, a = [x[k] for x in H if k in x], [x[k] for x in A if k in x]
        if len(h) < 30 or len(a) < 30:
            continue
        s = auc(a, h)
        op = ">" if s >= 0.5 else "<"
        u = umbral(h, op)
        filas[k] = {"mediana_humano": round(float(np.median(h)), 3), "mediana_ia": round(float(np.median(a)), 3),
                    "auc": round(s, 3), "op": op, "umbral": round(u, 3), "separa": abs(s - 0.5) >= 0.1,
                    "humanos_marcados": round(sum(marca(x, op, u) for x in h) / len(h), 3),
                    "ia_marcada": round(sum(marca(x, op, u) for x in a) / len(a), 3)}
    # una señal cuenta si separa y si su umbral marca a la IA bastante más que a los humanos
    senales = {k: (f["op"], f["umbral"]) for k, f in filas.items()
               if f["separa"] and f["ia_marcada"] - f["humanos_marcados"] >= 0.1}

    def cuantas(m):
        return sum(marca(m[k], op, u) for k, (op, u) in senales.items() if k in m)

    combinacion = {n: {"humanos": round(sum(cuantas(m) >= n for m in H) / len(H), 3),
                       "ia": round(sum(cuantas(m) >= n for m in A) / len(A), 3)} for n in range(1, 6)}
    modelos = sorted({r["modelo"] for r, _ in ia})
    por_modelo = {}
    for mod in modelos:
        sub = [m for r, m in ia if r["modelo"] == mod]
        por_modelo[mod] = {"n": len(sub), **{f"{n}+_senales": round(sum(cuantas(m) >= n for m in sub) / len(sub), 3)
                                             for n in (2, 3, 4)},
                           **{k: round(float(np.median([m[k] for m in sub if k in m])), 3) for k in senales}}
    res = {"corpus": corpus, "n_humano": len(H), "n_ia": len(A), "metricas": filas, "senales": senales,
           "combinacion": combinacion, "por_modelo": por_modelo}
    (RAIZ / f"resultado_{corpus}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    filas_csv = []
    for clase, grupo in (("humano", hum), ("ia", ia)):
        for r, m in grupo:
            filas_csv.append({"clase": clase, "pid": r["pid"], "modelo": r.get("modelo", ""), "anio": r.get("anio", ""),
                              "licencia": r.get("licencia", ""), "url": r.get("url", ""),
                              **{k: round(v, 4) for k, v in m.items()}})
    columnas = list(dict.fromkeys(k for f in filas_csv for k in f))
    with open(RAIZ / f"metricas_por_texto_{corpus}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas_csv)

    detalle = ", ".join(f"{m} {por_modelo[m]['n']}" for m in modelos)
    print(f"{corpus}: n humano {len(H)} | n IA {len(A)} ({detalle})")
    print(f"{'métrica':26s} {'hum':>7s} {'IA':>7s} {'AUC':>6s}  umbral      hum.marc  IA marc")
    for k, f in sorted(filas.items(), key=lambda x: -abs(x[1]['auc'] - 0.5)):
        print(f"{k:26s} {f['mediana_humano']:7.2f} {f['mediana_ia']:7.2f} {f['auc']:6.3f}  {f['op']} {f['umbral']:<8.3f} "
              f"{f['humanos_marcados']:7.1%} {f['ia_marcada']:7.1%} {'' if f['separa'] else '(no separa)'}")
    for n, v in combinacion.items():
        print(f"{n}+ señales: humanos {v['humanos']:.1%}, IA {v['ia']:.1%}")
    for mod, v in por_modelo.items():
        print(f"  {mod:22s} n={v['n']:3d}  3+ señales: {v['3+_senales']:.1%}")


if __name__ == "__main__":
    main()
