# Calibración de los umbrales

Fecha: 21 de octubre de 2026. Dos corpus pareados, como el de StoryScope: el tema es el mismo y lo único que cambia es
quién escribe. Cada texto de IA se pidió con una consigna neutra, que no pide ni prohíbe ningún estilo, sobre el
título de un texto humano. Solo entran textos de al menos 200 palabras de prosa.

| Modelo de IA | Cómo se usó |
|---|---|
| Claude Sonnet | CLI de Claude Code sin archivos de instrucciones del usuario ni ajustes (`--setting-sources` vacío) y con un system prompt neutro |
| GPT | `gpt-oss-20b`, el modelo abierto de OpenAI, por NVIDIA NIM. No es ChatGPT |
| Gemini Flash | `gemini-flash-latest`, por Google AI Studio |
| DeepSeek v4.1 Flash | por NVIDIA NIM |

Los textos no se publican, porque varias licencias no permiten obras derivadas. Los archivos
`metricas_por_texto_*.csv` traen el identificador, la URL, la licencia y las métricas de cada texto, y los scripts
de `scripts/` rearman los corpus completos.

## Método

Para cada métrica se midió el AUC, que es la probabilidad de que un texto de IA puntúe más alto que uno humano: 0.5
es no distinguir nada. El umbral es el valor más exigente que marca a lo sumo al 10% de los textos humanos (20% si
con 10% no marca a nadie, como pasa con las citas). Una métrica cuenta como señal si su AUC se aleja al menos 0.1 de
0.5 y si su umbral marca a la IA al menos 10 puntos más que a los humanos.

## Perfil académico

**Humano:** 298 introducciones de artículos de economía en español publicados en SciELO entre 2015 y 2020,
antes de los modelos de lenguaje masivos. Nueve revistas de Colombia, México y Perú, con licencias Creative Commons
leídas en cada página. **IA:** 390 introducciones sobre los mismos títulos. Consigna: "Escribe la introducción
de un artículo académico de economía titulado «…». Entre 350 y 550 palabras, en párrafos."

| Métrica | Mediana humana | Mediana IA | AUC | Umbral | Humanos marcados | IA marcada |
|---|---|---|---|---|---|---|
| Rayas por mil | 0.00 | 3.72 | 0.78 | más de 0.0 | 7.0% | 60.3% |
| Enumeraciones de tres por mil | 2.93 | 5.25 | 0.71 | más de 7.45 | 9.7% | 35.6% |
| Molde 'no es X, es Y' por mil | 0.00 | 0.00 | 0.61 | más de 1.4 | 9.7% | 30.8% |
| Léxico de IA por mil | 1.54 | 3.68 | 0.70 | más de 4.9 | 9.7% | 32.8% |
| Variación del largo de frase (CV) | 0.43 | 0.34 | 0.24 | menos de 0.33 | 9.2% | 42.6% |
| Citas (Autor, año) por mil palabras | 4.79 | 0.00 | 0.15 | menos de 1.45 | 19.5% | 82.8% |
| Nombres propios por mil | 29.75 | 15.02 | 0.22 | menos de 12.17 | 9.7% | 41.3% |

**Ninguna señal sola alcanza. La combinación sí:**

| Señales activas | Humanos | IA |
|---|---|---|
| 1 o más | 55.7% | 99.0% |
| 2 o más | 16.1% | 93.3% |
| 3 o más | 2.3% | 72.1% |
| 4 o más | 0.3% | 41.3% |
| 5 o más | 0.0% | 15.6% |

| Modelo | n | Con 3 o más señales |
|---|---|---|
| claude-sonnet | 100 | 78.0% |
| deepseek-v4.1-flash | 64 | 87.5% |
| gemini-flash-latest | 126 | 66.7% |
| gpt-oss-20b | 100 | 63.0% |

## Perfil redes

**Humano:** 250 posts de Global Voices en español escritos originalmente en español, de 2016 a 2020, con
licencia Creative Commons Atribución 3.0. Nueve de cada diez posts de ese sitio son traducciones del inglés y se
descartaron. Son textos de divulgación con firma, de autores de varios países de América Latina. **IA:** 240
textos sobre los mismos títulos. Consigna: "Escribe un artículo para un blog sobre «…». Entre 350 y 550 palabras, en
párrafos."

| Métrica | Mediana humana | Mediana IA | AUC | Umbral | Humanos marcados | IA marcada |
|---|---|---|---|---|---|---|
| Punto y coma por mil | 0.00 | 0.00 | 0.62 | más de 1.59 | 10.0% | 40.8% |
| Dos puntos por mil | 0.84 | 4.62 | 0.81 | más de 3.12 | 10.0% | 61.3% |
| Enumeraciones de tres por mil | 5.13 | 7.85 | 0.66 | más de 9.15 | 10.0% | 42.9% |
| Molde 'no es X, es Y' por mil | 0.00 | 2.08 | 0.79 | más de 1.07 | 10.0% | 63.7% |
| Léxico de IA por mil | 0.00 | 0.00 | 0.64 | más de 1.71 | 10.0% | 44.6% |
| Largo medio de frase (palabras) | 20.85 | 26.85 | 0.80 | más de 25.1 | 10.0% | 63.7% |
| Variación del largo de frase (CV) | 0.59 | 0.37 | 0.01 | menos de 0.5 | 8.0% | 93.8% |
| Variación del largo de párrafo (CV) | 0.47 | 0.16 | 0.01 | menos de 0.36 | 10.0% | 100.0% |
| Nombres propios por mil | 74.56 | 22.59 | 0.04 | menos de 48.22 | 10.0% | 85.4% |

| Señales activas | Humanos | IA |
|---|---|---|
| 1 o más | 63.6% | 100.0% |
| 2 o más | 20.8% | 100.0% |
| 3 o más | 3.6% | 97.9% |
| 4 o más | 0.0% | 93.8% |
| 5 o más | 0.0% | 75.8% |

| Modelo | n | Con 3 o más señales |
|---|---|---|
| claude-sonnet | 60 | 96.7% |
| deepseek-v4.1-flash | 60 | 96.7% |
| gemini-flash-latest | 60 | 100.0% |
| gpt-oss-20b | 60 | 98.3% |

## Lo que no funcionó

- **El punto y coma no delata a la IA en prosa académica.** Gemini lo usa mucho, pero Claude y GPT lo usan menos que
  los humanos (mediana de la IA 0.73, humana 1.49 por mil). En divulgación sí separa. En el perfil `estricto` sigue prohibido, pero por estilo, no porque delate.
- **La moraleja léxica** ("es decir", "por lo tanto", "en resumen") no separa en ninguno de los dos corpus. En prosa
  académica va incluso al revés: los humanos la usan más. La sobre-explicación que mide StoryScope es narrativa y no se
  reduce a esas palabras. Está apagada en `academico` y `redes`, y encendida en `narrativo`, que no está calibrado.
- **Las frases de más de 40 palabras** no separan: en prosa académica los humanos las escriben más largas. Es un asunto
  de legibilidad. Apagadas en `academico` y `redes`.
- **No separan en el corpus académico:** Punto y coma por mil, Conectores de manual por mil, Largo medio de frase (palabras), Relleno por mil, Frases de más de 40 palabras por mil.
- **No separan en el corpus de redes:** Rayas por mil, Moraleja léxica por mil, Conectores de manual por mil, Citas (Autor, año) por mil palabras, Relleno por mil, Frases de más de 40 palabras por mil.
- El relleno de manual ("Es importante destacar") ya casi no aparece en los modelos actuales con consigna neutra. Sigue
  como regla dura por estilo, no porque delate.

## Límites

- Dos dominios (artículos de economía y posts de divulgación) y cuatro modelos. GPT es el modelo abierto `gpt-oss-20b`,
  no el de ChatGPT, que solo se ofrece por API de pago.
- La falta de citas pesa mucho en el perfil académico porque la consigna no daba fuentes. Un texto de IA al que se le
  piden citas reales no tendría esa señal.
- En `redes`, la variación del largo de párrafo separa casi perfecto, en parte porque los posts periodísticos alternan
  párrafos cortos y largos. Un post de Instagram o de LinkedIn puede tener otra forma.
- El perfil `narrativo` no está calibrado: usa las señales de `redes` y la moraleja encendida por criterio.
- Ninguna combinación de señales prueba autoría. Entre el 2% y el 4% de los textos humanos también activa tres o más.
