"""Reglas de revisión. Cada regla devuelve hallazgos con su ubicación exacta en el texto.

Las reglas no reescriben nada. Miden y señalan. La decisión de corregir es de quien escribe.
"""

import re
import statistics
import tomllib
from dataclasses import dataclass, field
from importlib import resources

from .lector import frases

DESCRIPCION = {
    "punto_y_coma": "Punto y coma",
    "rayas": "Rayas explicativas (— o –)",
    "relleno": "Frases de relleno típicas de IA",
    "comillas_enfasis": "Comillas que no citan a nadie",
    "dos_puntos": "Exceso de dos puntos (molde 'afirmación: prueba')",
    "moraleja": "Sobre-explicación: le dice al lector qué concluir",
    "cierre_moraleja": "Párrafo que cierra con la moraleja o repitiendo lo dicho",
    "frases_largas": "Frase demasiado larga",
    "ritmo_uniforme": "Ritmo uniforme: las frases miden casi lo mismo",
    "parrafos_clonados": "Párrafos clonados en extensión",
    "tricolon": "Enumeraciones de tres en serie",
    "contraste": "Molde 'no es X, es Y'",
    "conectores": "Conectores de manual",
    "arranques_repetidos": "Frases que arrancan igual",
    "lexico_ia": "Léxico que los modelos usan de más",
    "moldes": "Moldes retóricos de asistente o de redes",
    "especificidad": "Texto genérico: pocas citas o nombres concretos",
    "emojis": "Emojis",
}

COMO_CORREGIR = {
    "punto_y_coma": "Partir en dos frases o usar coma",
    "rayas": "Reescribir con comas, paréntesis o una frase aparte",
    "relleno": "Borrar la frase y decir directamente lo que viene después",
    "comillas_enfasis": "Quitar las comillas. Si la palabra necesita énfasis, cambiar la palabra",
    "dos_puntos": "Reescribir con punto, coma o subordinada. Variar la solución",
    "moraleja": "Borrar la interpretación y dejar el dato. El lector puede inferir",
    "cierre_moraleja": "Cortar la última frase o reemplazarla por un dato nuevo",
    "frases_largas": "Partir la frase",
    "ritmo_uniforme": "Intercalar frases cortas y secas entre las largas",
    "parrafos_clonados": "Fusionar o partir párrafos según la idea, no según el molde",
    "tricolon": "Dejar dos elementos, o cuatro, o pasar la lista a prosa",
    "contraste": "Afirmar lo que es, sin negar primero lo que no es",
    "conectores": "Quitar el conector. Casi siempre sobra",
    "arranques_repetidos": "Cambiar el sujeto o el orden de la frase",
    "lexico_ia": "Cambiar por una palabra más concreta o más común",
    "moldes": "Reescribir sin la fórmula",
    "especificidad": "Nombrar autores, textos, lugares y cifras en vez de aludir",
    "emojis": "Quitarlos",
}


@dataclass
class Ubicacion:
    ref: int       # párrafo del documento original
    bloque: int    # índice del bloque de prosa
    inicio: int
    fin: int
    extracto: str


@dataclass
class Hallazgo:
    regla: str
    severidad: str
    mensaje: str
    valor: float | None = None
    tope: float | None = None
    ubicaciones: list = field(default_factory=list)

    @property
    def descripcion(self):
        return DESCRIPCION[self.regla]

    @property
    def como_corregir(self):
        return COMO_CORREGIR[self.regla]


# ------------------------------------------------------------------ configuración
def _cargar_toml(paquete, nombre):
    return tomllib.loads(resources.files(paquete).joinpath(nombre).read_text(encoding="utf-8"))


def perfiles_disponibles():
    carpeta = resources.files("humanizador.perfiles")
    return sorted(p.name[:-5] for p in carpeta.iterdir() if p.name.endswith(".toml"))


def cargar_perfil(nombre_o_ruta):
    from pathlib import Path

    ruta = Path(str(nombre_o_ruta))
    if ruta.suffix == ".toml" and ruta.exists():
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    else:
        if nombre_o_ruta not in perfiles_disponibles():
            raise ValueError(f"perfil desconocido: {nombre_o_ruta}. Disponibles: {', '.join(perfiles_disponibles())}")
        datos = _cargar_toml("humanizador.perfiles", f"{nombre_o_ruta}.toml")
    if "hereda" in datos:
        base = cargar_perfil(datos["hereda"])
        for seccion in ("severidad", "umbrales"):
            base[seccion] = {**base.get(seccion, {}), **datos.get(seccion, {})}
        base["nombre"] = ruta.stem if ruta.suffix == ".toml" else nombre_o_ruta
        base["descripcion"] = datos.get("descripcion", base.get("descripcion", ""))
        return base
    datos["nombre"] = ruta.stem if ruta.suffix == ".toml" else nombre_o_ruta
    return datos


def cargar_catalogo():
    cat = _cargar_toml("humanizador", "catalogo.toml")
    compilado = {k: [re.compile(p, re.I | re.M) for p in v] for k, v in cat.items() if k != "conectores"}
    compilado["conectores"] = [re.compile(rf"(?<![\wáéíóúñ]){re.escape(c)}(?![\wáéíóúñ])", re.I)
                               for c in cat["conectores"]]
    return compilado


# ------------------------------------------------------------------ utilidades
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]")
_ARTICULO = r"(?:(?:el|la|los|las|un|una|unos|unas|de|del|al|a|en|con|por|su|sus) )*"
_ITEM = r"[a-záéíóúñü]+(?: [a-záéíóúñü]+){0,2}"
# tres elementos cortos en serie, sin mayúsculas ni cifras, para no confundir autores o años con un tricolon
TRICOLON = re.compile(rf"(?<![\wáéíóúñ]){_ITEM}, {_ITEM},? (?:y|o|e|u) {_ARTICULO}[a-záéíóúñü]{{3,}}")
CITA = re.compile(r"\([A-ZÁÉÍÓÚ][^()]{1,80}\d{4}[a-z]?[^()]*\)|[A-ZÁÉÍÓÚ][\wáéíóúñ-]+(?: et al\.)? \(\d{4}")
NOMBRE_PROPIO = re.compile(r"(?<=[a-záéíóúñ,;] )[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}")


def _palabras(t):
    return set(re.findall(r"[a-záéíóúñü]{4,}", t.lower()))


def _extracto(texto, a, b, ancho=60):
    i, j = max(0, a - ancho), min(len(texto), b + ancho)
    return ("…" if i else "") + texto[i:j].replace("\n", " ") + ("…" if j < len(texto) else "")


# ------------------------------------------------------------------ revisión
def revisar(bloques, perfil="academico"):
    P = cargar_perfil(perfil) if isinstance(perfil, str) else perfil
    sev, U = P["severidad"], P["umbrales"]
    cat = cargar_catalogo()
    n_pal = sum(len(b.texto.split()) for b in bloques) or 1
    por_mil = lambda k: round(k * 1000 / n_pal, 2)
    hallazgos, metricas = [], {"palabras": n_pal, "parrafos": len(bloques)}
    encontrados = {k: [] for k in DESCRIPCION}

    def ubic(regla, i, b, a, z):
        encontrados[regla].append(Ubicacion(b.ref, i, a, z, _extracto(b.texto, a, z)))

    for i, b in enumerate(bloques):
        t = b.texto
        # el punto y coma que separa citas dentro de un paréntesis (APA) no es un tic
        en_citas = [(m.start(), m.end()) for m in re.finditer(r"\([^()]*\d{4}[^()]*\)", t)]
        for m in re.finditer(r";", t):
            if not any(a < m.start() < z for a, z in en_citas):
                ubic("punto_y_coma", i, b, m.start(), m.end())
        for m in re.finditer(r"[—–]", t):
            ubic("rayas", i, b, m.start(), m.end())
        for regla in ("relleno", "moraleja", "contraste", "lexico_ia", "moldes", "conectores"):
            vistos = set()
            for p in cat[regla]:
                for m in p.finditer(t):
                    if not any(m.start() < z and a < m.end() for a, z in vistos):
                        vistos.add((m.start(), m.end()))
                        ubic(regla, i, b, m.start(), m.end())
        for m in re.finditer(r"[\"“«]([^\"”»]{1,40})[\"”»]", t):
            if len(m.group(1).split()) <= 4:
                ubic("comillas_enfasis", i, b, m.start(), m.end())
        for m in re.finditer(r":(?!\d|//)", t):
            # no cuentan los que cierran el bloque (presentan ecuación, lista o tabla) ni las etiquetas cortas
            # al inicio del bloque ("Integrantes: …")
            if t[m.end():].strip() and len(t[:m.start()].split()) > 3:
                ubic("dos_puntos", i, b, m.start(), m.end())
        for m in TRICOLON.finditer(t):
            ubic("tricolon", i, b, m.start(), m.end())
        for m in EMOJI.finditer(t):
            ubic("emojis", i, b, m.start(), m.end())

        fs = frases(t)
        for f, a, z in fs:
            if len(f.split()) > U["frase_larga_palabras"]:
                ubic("frases_largas", i, b, a, z)
        if len(fs) >= 3:
            f, a, z = fs[-1]
            ult, previo = _palabras(f), _palabras(" ".join(x[0] for x in fs[:-1]))
            repite = len(ult) >= 4 and len(ult & previo) / len(ult) >= 0.7
            if repite or any(p.search(f) for p in cat["moraleja"]):
                ubic("cierre_moraleja", i, b, a, z)

    def agregar(regla, mensaje, valor=None, tope=None, ubicaciones=None):
        if sev.get(regla, "blanda") == "apagada":
            return
        hallazgos.append(Hallazgo(regla, sev.get(regla, "blanda"), mensaje, valor, tope, ubicaciones or []))

    # reglas por densidad: se disparan solo si pasan el tope del perfil
    for regla in ("punto_y_coma", "rayas", "dos_puntos", "moraleja", "tricolon", "contraste", "conectores",
                  "lexico_ia", "moldes"):
        valor = por_mil(len(encontrados[regla]))
        metricas[f"{regla}_x1000"] = valor
        if encontrados[regla] and valor > U[regla]:
            agregar(regla, f"{valor} por mil palabras (tope {U[regla]})", valor, U[regla], encontrados[regla])
    # reglas de tolerancia cero
    for regla in ("relleno", "comillas_enfasis", "emojis", "frases_largas", "cierre_moraleja"):
        metricas[f"{regla}_n"] = len(encontrados[regla])
        if encontrados[regla]:
            agregar(regla, f"{len(encontrados[regla])} casos", len(encontrados[regla]), 0, encontrados[regla])

    # ritmo
    todas = [(i, b, f, a, z) for i, b in enumerate(bloques) for f, a, z in frases(b.texto)]
    largos = [len(x[2].split()) for x in todas]
    if len(largos) >= 8:
        cv = statistics.pstdev(largos) / statistics.mean(largos)
        metricas.update({"frases": len(largos), "largo_medio_frase": round(statistics.mean(largos), 1),
                         "cv_largo_frase": round(cv, 2)})
        if cv < U["cv_frase_minimo"]:
            agregar("ritmo_uniforme", f"coeficiente de variación {cv:.2f} (mínimo {U['cv_frase_minimo']})",
                    round(cv, 2), U["cv_frase_minimo"])
    lp = [len(b.texto.split()) for b in bloques]
    if len(lp) >= 6:
        cvp = statistics.pstdev(lp) / statistics.mean(lp)
        metricas["cv_largo_parrafo"] = round(cvp, 2)
        if cvp < U["cv_parrafo_minimo"]:
            agregar("parrafos_clonados", f"coeficiente de variación {cvp:.2f} (mínimo {U['cv_parrafo_minimo']})",
                    round(cvp, 2), U["cv_parrafo_minimo"])
    aperturas = {}
    for i, b, f, a, z in todas:
        aperturas.setdefault(" ".join(f.split()[:2]).lower(), []).append(Ubicacion(b.ref, i, a, z, f[:120]))
    repetidas = {k: v for k, v in aperturas.items()
                 if len(v) >= 4 and len(v) / max(len(todas), 1) > U["arranque_repetido_fraccion"]}
    if repetidas:
        agregar("arranques_repetidos", ", ".join(f"'{k}' ×{len(v)}" for k, v in repetidas.items()),
                ubicaciones=[u for v in repetidas.values() for u in v])

    # especificidad
    texto = "\n".join(b.texto for b in bloques)
    citas, nombres = por_mil(len(CITA.findall(texto))), por_mil(len(NOMBRE_PROPIO.findall(texto)))
    metricas.update({"citas_x1000": citas, "nombres_propios_x1000": nombres})
    faltan = []
    if U["citas_minimas"] and citas < U["citas_minimas"]:
        faltan.append(f"{citas} citas por mil palabras (mínimo {U['citas_minimas']})")
    if U["nombres_minimos"] and nombres < U["nombres_minimos"]:
        faltan.append(f"{nombres} nombres propios por mil palabras (mínimo {U['nombres_minimos']})")
    if faltan:
        agregar("especificidad", " y ".join(faltan))

    orden = {"dura": 0, "blanda": 1}
    hallazgos.sort(key=lambda h: (orden[h.severidad], list(DESCRIPCION).index(h.regla)))
    return Resultado(P["nombre"], metricas, hallazgos, senales_calibradas(metricas))


# Las ocho métricas que separaron humano de IA en la calibración, con su umbral del perfil académico.
# Se cuentan siempre con esos umbrales, sea cual sea el perfil elegido, porque son los que se midieron.
SENALES = {
    "citas_x1000": ("<", "citas_minimas", "Sin citas (Autor, año)"),
    "nombres_propios_x1000": ("<", "nombres_minimos", "Pocos nombres propios"),
    "rayas_x1000": (">", "rayas", "Rayas"),
    "cv_largo_frase": ("<", "cv_frase_minimo", "Frases de largo parejo"),
    "tricolon_x1000": (">", "tricolon", "Enumeraciones de tres"),
    "lexico_ia_x1000": (">", "lexico_ia", "Léxico de IA"),
    "dos_puntos_x1000": (">", "dos_puntos", "Dos puntos"),
    "punto_y_coma_x1000": (">", "punto_y_coma", "Punto y coma"),
}


def senales_calibradas(metricas):
    U = cargar_perfil("academico")["umbrales"]
    activas = []
    for clave, (op, umbral, nombre) in SENALES.items():
        if clave not in metricas:
            continue
        v, u = metricas[clave], U[umbral]
        if (v < u) if op == "<" else (v > u):
            activas.append(nombre)
    return activas


@dataclass
class Resultado:
    perfil: str
    metricas: dict
    hallazgos: list
    senales: list = field(default_factory=list)

    @property
    def duras(self):
        return [h for h in self.hallazgos if h.severidad == "dura"]

    @property
    def blandas(self):
        return [h for h in self.hallazgos if h.severidad == "blanda"]

    @property
    def pasa(self):
        return not self.duras

    def a_dict(self):
        return {"perfil": self.perfil, "pasa": self.pasa, "metricas": self.metricas, "senales_calibradas": self.senales,
                "hallazgos": [{"regla": h.regla, "descripcion": h.descripcion, "severidad": h.severidad,
                               "mensaje": h.mensaje, "como_corregir": h.como_corregir,
                               "ubicaciones": [u.__dict__ for u in h.ubicaciones]} for h in self.hallazgos]}
