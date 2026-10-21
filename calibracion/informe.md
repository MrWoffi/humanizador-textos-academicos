# Calibración de los umbrales

Fecha: 21 de octubre de 2026.

## Corpus

| Lado | Qué es | n |
|---|---|---|
| Humano | Introducciones de artículos de economía en español publicados en SciELO entre 2015 y 2020, antes de los modelos de lenguaje masivos. Nueve revistas: seis de Colombia (219 textos), dos de México (42) y una del Perú (37). Licencias Creative Commons leídas en cada página | 298 |
| IA | Introducciones escritas por modelos sobre **los mismos títulos**, con una consigna neutra que no pide ni prohíbe ningún estilo: "Escribe la introducción de un artículo académico de economía titulado «…». Entre 350 y 550 palabras, en párrafos." Gemini Flash (126) y DeepSeek v4.1 Flash (64) | 190 |

Es un corpus pareado, como el de StoryScope: el tema es el mismo y lo único que cambia es quién escribe. Solo
entran textos de al menos 200 palabras de prosa.

Los textos no se publican, porque varias licencias de SciELO no permiten obras derivadas. En
`metricas_por_texto.csv` están el identificador, la URL, la licencia y las métricas de cada uno, y los
scripts de `scripts/` rearman el corpus completo.

## Método

Para cada métrica se midió el AUC: la probabilidad de que un texto de IA puntúe más alto que uno humano. Un
AUC de 0.5 significa que la métrica no distingue. El umbral es el **percentil 90 humano** cuando la IA puntúa
más alto, o el percentil 10 cuando puntúa más bajo. Así cada regla marca solo lo que un humano hace rara vez,
y su tasa de falsos positivos queda cerca del 10%.

## Resultados

| Métrica | Mediana humana | Mediana IA | AUC | Umbral | Humanos marcados | IA marcada |
|---|---|---|---|---|---|---|
| Citas (Autor, año) por mil palabras | 4.8 | 0.0 | 0.11 | menos de 1.0 | 16.8% | 92.6% |
| Rayas por mil palabras | 0.0 | 4.0 | 0.78 | más de 0 | 7.0% | 61.6% |
| Nombres propios por mil palabras | 29.8 | 13.9 | 0.22 | menos de 12.5 | 10.1% | 46.8% |
| Variación del largo de frase (CV) | 0.43 | 0.36 | 0.25 | menos de 0.33 | 9.1% | 33.2% |
| Enumeraciones de tres por mil | 2.9 | 5.9 | 0.71 | más de 7.4 | 10.1% | 41.6% |
| Léxico de IA por mil | 1.5 | 3.9 | 0.70 | más de 4.9 | 9.7% | 30.0% |
| Dos puntos por mil | 1.5 | 2.2 | 0.70 | más de 4.4 | 9.7% | 17.9% |
| Punto y coma por mil | 1.5 | 4.0 | 0.60 | más de 6.3 | 10.1% | 24.2% |

**Ninguna señal sola alcanza. La combinación sí:**

| Señales activas (de las 8) | Humanos | IA |
|---|---|---|
| 1 o más | 57.0% | 100.0% |
| 2 o más | 19.5% | 93.7% |
| 3 o más | 5.0% | 76.3% |
| 4 o más | 1.0% | 50.5% |

Por eso el reporte cuenta cuántas de las ocho están activas.

## Lo que no funcionó

- **Moraleja léxica** ("es decir", "por lo tanto", "en resumen"): AUC 0.33, al revés de lo esperado. En prosa
  académica humana esas fórmulas son *más* frecuentes que en la de IA. La sobre-explicación que mide
  StoryScope es narrativa, y en un artículo no se reduce a palabras. Quedó apagada en el perfil académico.
- **Frases de más de 40 palabras:** los humanos escriben frases más largas (mediana 36 contra 33). Es un
  asunto de legibilidad, no una huella de IA. Apagada en el perfil académico.
- **Relleno, moldes, contraste, conectores, comillas de énfasis y cierre con moraleja:** AUC entre 0.43 y
  0.59. En introducciones académicas son raros en los dos lados, porque los modelos actuales ya no escriben
  "Es importante destacar" con consigna neutra. El relleno sigue como regla dura por gusto de estilo, no
  porque delate a la IA.

## Límites

- Un solo dominio (economía), una sola sección (introducciones) y dos modelos. Otros modelos u otras
  disciplinas pueden dar otros umbrales.
- La falta de citas pesa mucho porque la consigna no daba fuentes. Un texto de IA al que se le piden citas
  reales no tendría esa señal.
- Los perfiles `redes` y `narrativo` no están calibrados: sus umbrales siguen siendo de criterio.
- Ninguna combinación de señales es prueba de autoría. El 5% de los humanos también activa tres o más.
