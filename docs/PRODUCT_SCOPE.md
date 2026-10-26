# Prioridades del producto

Requisito del usuario: analizar la acción que solicite en cada ocasión, con un horizonte principal de **3–6 meses**. No limitar la aplicación a AAPL, a una lista de ejemplos ni a una sola empresa. The Windows local Qwen synthetic structured-output check passed; the first real-source synthesis was rejected and needs diagnosis. Financial-quality validation remains pending. See LOCAL_AI.md and LOCAL_WINDOWS_CHECK.json. No activar servicios IA de pago.

## Enfoque del análisis

1. Resultados próximos y cambios en guidance, con fechas y fuentes confirmadas.
2. Noticias, catalizadores y riesgos relevantes para los próximos 3–6 meses; distinguir hechos, inferencias e hipótesis.
3. Momentum, volumen, volatilidad y comparación con benchmark cuando haya datos suficientes. No convertir indicadores descriptivos en predicciones sin evaluación.
4. Escenarios bajista/base/alcista para el horizonte, condiciones que invalidarían la tesis y seguimiento de cambios. El motor manual EPS forward × P/E a 3/6 meses está implementado con dividendos explícitos, evidencia y versiones; su automatización, calibración y validación predictiva siguen pendientes. Los escenarios DCF expresan valor presente.
5. Fundamentales, fortaleza financiera y valoración como contexto para interpretar el riesgo. El DCF de 5–10 años no constituye un objetivo bursátil a 3 o 6 meses.

Quick y Deep son profundidades de investigación distintas para el mismo horizonte, no estrategias de corto y largo plazo. Las ventanas retrospectivas de noticias (30/90/365 días) tampoco son el plazo de inversión.

## Tickers y cobertura

La búsqueda, investigación y motores reciben el ticker seleccionado por el usuario. Los tickers de portada son ejemplos. Cada investigación debe conservar su símbolo, fuentes, fechas y moneda; no reutilizar el contexto de otra empresa.

Los adaptadores actuales cubren emisores SEC y cotizaciones de instrumentos US verificables en Finnhub, incluidos algunos emisores extranjeros. No equivale a cobertura de todas las bolsas del mundo. Ampliar mercados requiere identificar bolsa, símbolo, divisa, proveedor y derechos de acceso. Si una acción no tiene cobertura, explicarlo sin sustituirla por otra empresa ni inventar datos.

## Estado del horizonte

Investigaciones nuevas: rango 3–6 meses predeterminado, con opciones de 3 o 6 meses. Se guarda fecha base UTC y ventana de fechas calculada por meses naturales, conservadas en JSON/PDF. Expedientes antiguos sin horizonte permanecen identificados como tales.

Además del horizonte, hay calendario de resultados estimados de Finnhub, registro manual de catalizadores con versiones y escenarios condicionales de precio a 3/6 meses. No implican un pronóstico validado, tesis automática ni señales de entrada/salida. A local connector now generates bounded, quote-checked claims. Richer qualitative analysis, semantic retrieval, full source coverage and quality evaluation remain pending.
