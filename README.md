# Humanizador de textos académicos

Mide la huella de IA en textos en español y la marca sobre el propio documento. **Mide, no reescribe.**

Le pasas un Word, un Markdown, un HTML o un texto plano y te devuelve qué patrones de escritura de IA
tiene, dónde están y cómo corregir cada uno. Con `--marcar` te devuelve una copia del Word con cada
hallazgo resaltado y comentado al margen.

```bash
uvx --from git+https://github.com/MrWoffi/humanizador-textos-academicos humanizador informe.docx --marcar
```

## Lo que no es

- **No es un detector de IA.** No dice si un texto lo escribió una máquina. Dice si tiene los vicios que
  delatan a una máquina, que también tienen muchos textos humanos apurados.
- **No garantiza pasar Turnitin, GPTZero ni ningún otro detector.** Quien lo prometa, miente.
- **No reescribe.** Un texto retorcido para engañar a un clasificador es igual de artificial. La
  corrección la decide quien escribe.

## Instalación

Necesitas [uv](https://docs.astral.sh/uv/). Para usarlo sin instalar nada:

```bash
uvx --from git+https://github.com/MrWoffi/humanizador-textos-academicos humanizador archivo.docx
```

Para tenerlo siempre disponible:

```bash
uv tool install git+https://github.com/MrWoffi/humanizador-textos-academicos
humanizador archivo.docx
```

## Uso

```bash
humanizador tesis.docx                      # reporte en la terminal, perfil académico
humanizador tesis.docx --marcar             # copia "tesis (revisado).docx" con resaltado y comentarios
humanizador post.md --perfil redes --html   # reporte HTML con el texto marcado
humanizador capitulo.docx --json            # salida para otros programas
humanizador informe.docx --perfil mi_estilo.toml
```

Sale con código 1 si alguna regla dura falla, así que sirve en un flujo automático.

En un Word solo revisa la prosa. Salta títulos, leyendas de figuras y tablas, notas, ecuaciones y todo
lo que viene después de "Referencias". El marcado no cambia una sola letra del documento: solo agrega
resaltado (rosa para reglas duras, amarillo para señales) y un comentario por hallazgo.

## Perfiles

| Perfil | Para qué | Qué cambia |
|---|---|---|
| `academico` (defecto) | Informes, tesis, artículos | El punto y coma y la raya son correctos en español académico: solo se vigila su abuso |
| `estricto` | Estilo personal sin concesiones | Cero punto y coma, cero rayas, cero comillas de énfasis, pocos dos puntos, todo como regla dura |
| `redes` | Posts, artículos de blog, guiones de reel, correos | Calibrado aparte, con textos de divulgación. Pide nombres propios en vez de citas |
| `narrativo` | Guiones con historia, relatos | Usa las señales de `redes` y vuelve a encender la moraleja explícita. Sin calibrar |

Un perfil es un `.toml` de dos tablas: `[severidad]` dice si cada regla es `dura`, `blanda` o `apagada`, y
`[umbrales]` fija los topes. Para hacer el tuyo, hereda uno y cambia solo lo que quieras:

```toml
hereda = "academico"

[severidad]
punto_y_coma = "dura"

[umbrales]
dos_puntos = 2.0
```

Un ejemplo de por qué existen los perfiles: **"Nuestra América" de José Martí (1891) pasa el perfil
académico y falla el estricto** por sus punto y coma y unas comillas irónicas. El estricto describe un
gusto, no una norma del idioma. Martí está en `tests/casos/` como prueba de que el revisor no confunde
la buena prosa humana con la de una máquina.

## Qué mide

**Reglas que marcan relleno y tics de formato**

| Regla | Qué cuenta |
|---|---|
| Relleno | "Es importante destacar", "Cabe señalar", "juega un papel crucial", "En conclusión", "En el mundo actual"… |
| Punto y coma, rayas | Por cada mil palabras. Prohibidos en el perfil estricto |
| Comillas de énfasis | Comillas alrededor de una a cuatro palabras que no citan a nadie |
| Dos puntos | El molde "afirmación: prueba" ("La producción es persistente: su coeficiente…"). No cuentan los que presentan una ecuación, lista o tabla, ni las etiquetas cortas |
| Léxico de IA | "fomentar", "potenciar", "abordar", "integral", "robusto", "en el ámbito de"… por densidad, no por prohibición |
| Moldes | "¿El resultado?", "Imagina…", "La verdad es que", "de manera efectiva", "claro y conciso"… |
| Emojis | En textos académicos |

**Señales de sobre-explicación, basadas en StoryScope**

[StoryScope](https://arxiv.org/abs/2604.03136v1) (arXiv 2604.03136, 2026) comparó 10,272 consignas
escritas por un humano y por cinco modelos de lenguaje, 61,608 historias en total. Mirando solo la
estructura narrativa, sin el estilo, separa humano de IA con 93.2% de F1. Su hallazgo central es la
**sobre-determinación**: la IA escribe como si el lector no pudiera inferir. Explica el tema en el 77% de
sus historias, cierra todos los cabos y termina con la lección. Los humanos nombran autores, textos y
lugares casi el doble.

| Señal | Qué cuenta |
|---|---|
| Moraleja | "esto demuestra que", "es decir", "en otras palabras", "la clave está", "por lo tanto"… Solo en `narrativo`: la calibración mostró que no delata a la IA ni en prosa académica ni en divulgación |
| Cierre con moraleja | Párrafos cuya última frase repite lo ya dicho o anuncia la conclusión |
| Ritmo uniforme | Frases y párrafos de largo parecido (coeficiente de variación bajo) |
| Frases largas | Más de 40 palabras. Es legibilidad, no huella de IA: apagada en `academico` y `redes` |
| Tricolon | Enumeraciones de tres en serie, "X, Y y Z" |
| Contraste | "No es X, es Y" |
| Conectores | "Además", "Sin embargo", "Por otro lado"… por encima del tope |
| Arranques repetidos | La misma apertura en más del 3% de las frases |
| Especificidad | Pocas citas (Autor, año) en académico, pocos nombres propios en redes |

StoryScope estudia ficción. De él se toma lo que vale para cualquier texto, la sobre-explicación, y no
sus reglas propias de la narrativa (romper la cuarta pared, sueños, cronología rota). Sus cifras
describen relatos en inglés, no prosa académica en español.

## De dónde salen los umbrales

Los umbrales de los perfiles `academico` y `redes` están medidos, no puestos a ojo. Para cada uno se comparó un
corpus de textos humanos escritos antes de los modelos de lenguaje con textos de IA escritos **sobre los mismos
títulos** por cuatro modelos: Claude Sonnet, GPT (`gpt-oss-20b`, el modelo abierto de OpenAI), Gemini Flash y
DeepSeek v4.1 Flash.

| Perfil | Textos humanos | Textos de IA |
|---|---|---|
| `academico` | 298 introducciones de artículos de economía en SciELO, 2015-2020 | 390 |
| `redes` | 250 posts de Global Voices escritos originalmente en español, 2016-2020 | 240 |

Cada umbral marca solo lo que un humano hace rara vez (a lo sumo el 10% de los textos humanos). Ninguna señal basta
sola, pero juntas sí:

| Perfil | Con 3 o más señales: humanos | IA | Claude | GPT | Gemini | DeepSeek |
|---|---|---|---|---|---|---|
| `academico` | 2.3% | 72.1% | 78.0% | 63.0% | 66.7% | 87.5% |
| `redes` | 3.6% | 97.9% | 96.7% | 98.3% | 100.0% | 96.7% |

Por eso cada reporte termina contando cuántas señales se activaron. En prosa académica las que más separan son la
falta de citas (Autor, año), las rayas, los pocos nombres propios y el largo de frase parejo. En divulgación, el largo
de párrafo y de frase parejos, los pocos nombres propios, los dos puntos y el molde "no es X, es Y".

También se midió lo que **no** funciona. La moraleja léxica ("es decir", "por lo tanto") no separa en ninguno de los
dos corpus: en prosa académica los humanos la usan más. El punto y coma no delata a la IA en textos académicos, porque
Claude y GPT lo usan menos que los humanos. Las frases largas son más humanas que artificiales. Todo eso quedó apagado.

El detalle, los límites y los scripts para repetir la medición están en
[`calibracion/informe.md`](calibracion/informe.md). El perfil `narrativo` todavía no está calibrado.

## Para ampliarlo

Los patrones están en `src/humanizador/catalogo.toml`. Para sumar un tic, agrégalo a su lista y corre las
pruebas:

```bash
uv run --group dev pytest
```

## Licencia

MIT. Hecho por Rodrigo Ferrer en [Altrion Partners](https://altrionpartners.com).
