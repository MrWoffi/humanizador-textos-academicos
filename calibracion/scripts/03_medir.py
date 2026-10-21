"""Mide las métricas del paquete humanizador sobre introducciones humanas (SciELO 2015-2020) y de IA.

Por métrica: medianas, AUC (probabilidad de que un texto de IA puntúe más alto que uno humano) y el umbral
que marca solo lo que un humano rara vez hace: percentil 90 humano si la IA puntúa más alto, percentil 10
humano si puntúa más bajo.
"""

import ast
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from humanizador.lector import Bloque, es_prosa  # noqa: E402
from humanizador.reglas import revisar  # noqa: E402

DATOS = Path(__file__).resolve().parents[1] / "datos"  # los textos no se publican: se rearman con 01 y 02


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
    for k in ("relleno_n", "comillas_enfasis_n", "frases_largas_n", "cierre_moraleja_n", "emojis_n"):
        m[k.replace("_n", "_x1000")] = m.pop(k) * 1000 / pal
    return m


def auc(ia, hu):
    ia, hu = np.asarray(ia), np.asarray(hu)
    mayor = (ia[:, None] > hu[None, :]).mean()
    empate = (ia[:, None] == hu[None, :]).mean()
    return float(mayor + empate / 2)


def main():
    hu = [metricas(b) for _, b in cargar("scielo_humano.jsonl")]
    ia_reg = cargar("ia_generado.jsonl")
    ia = [metricas(b) for _, b in ia_reg]
    claves = [k for k in hu[0] if k not in ("palabras", "parrafos", "frases")]
    filas = {}
    for k in claves:
        h = [x[k] for x in hu if k in x]
        a = [x[k] for x in ia if k in x]
        if len(h) < 30 or len(a) < 30:
            continue
        s = auc(a, h)
        sube = s >= 0.5
        umbral = float(np.percentile(h, 90 if sube else 10))
        filas[k] = {"mediana_humano": round(float(np.median(h)), 3), "mediana_ia": round(float(np.median(a)), 3),
                    "auc": round(s, 3), "ia_marca": "alto" if sube else "bajo",
                    "umbral_p90_humano" if sube else "umbral_p10_humano": round(umbral, 3),
                    "separa": abs(s - 0.5) >= 0.1,
                    "humanos_marcados_con_umbral_actual": None}
    por_modelo = {}
    for modelo in sorted({r["modelo"] for r, _ in ia_reg}):
        sub = [metricas(b) for r, b in ia_reg if r["modelo"] == modelo]
        por_modelo[modelo] = {"n": len(sub), **{k: round(float(np.median([x[k] for x in sub if k in x])), 3)
                                                 for k in claves if all(k in x for x in sub)}}
    res = {"n_humano": len(hu), "n_ia": len(ia), "metricas": filas, "medianas_por_modelo": por_modelo}
    (DATOS.parent / "resultado_paquete.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                                         encoding="utf-8")
    print(f"n humano {len(hu)} | n IA {len(ia)}")
    print(f"{'métrica':28s} {'med hum':>8s} {'med IA':>8s} {'AUC':>6s}  umbral")
    for k, f in sorted(filas.items(), key=lambda x: -abs(x[1]['auc'] - 0.5)):
        u = f.get("umbral_p90_humano", f.get("umbral_p10_humano"))
        print(f"{k:28s} {f['mediana_humano']:8.3f} {f['mediana_ia']:8.3f} {f['auc']:6.3f}  "
              f"{'>' if f['ia_marca'] == 'alto' else '<'} {u:.3f} {'' if f['separa'] else '(no separa)'}")



def tasas(umbrales):
    hu = [metricas(b) for _, b in cargar("scielo_humano.jsonl")]
    ia = [metricas(b) for _, b in cargar("ia_generado.jsonl")]
    for k, (op, u) in umbrales.items():
        f = (lambda v: v > u) if op == ">" else (lambda v: v < u)
        th = sum(f(x[k]) for x in hu if k in x) / len(hu)
        ti = sum(f(x[k]) for x in ia if k in x) / len(ia)
        print(f"{k:24s} {op} {u:<6} marca {th:5.1%} de humanos y {ti:5.1%} de IA")
    def cuantas(x):
        return sum(((x[k] > u) if op == ">" else (x[k] < u)) for k, (op, u) in umbrales.items() if k in x)
    for n in (1, 2, 3, 4):
        print(f"con {n}+ señales: humanos {sum(cuantas(x) >= n for x in hu)/len(hu):5.1%}, IA {sum(cuantas(x) >= n for x in ia)/len(ia):5.1%}")


if __name__ == "__main__":
    main()
