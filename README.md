# Stock Intelligence AI

Workspace personal de investigación financiera con datos reales de SEC y Finnhub, motor financiero determinista, historial y expedientes exportables. Next.js / React / TypeScript, FastAPI / Pydantic, SQLAlchemy y SQLite.

**Objetivo principal:** analizar la acción que el usuario solicite para **3–6 meses**. Noticias, resultados, catalizadores y riesgo de precio; fundamentales y DCF como contexto. Los tickers de portada son ejemplos, no una lista cerrada. La cobertura actual depende de SEC/Finnhub US; no se declara acceso a todas las bolsas. [Prioridades del producto](docs/PRODUCT_SCOPE.md).

**Status:** local Qwen research runs on Windows. Review of its 16-claim export found financial-period/unit and source-context errors. A [quality update](docs/RESEARCH_QUALITY.md) now displays structured financial facts, withholds flagged numerical claims, preserves complete-sentence context and audits issuer links. Its tests/build pass; execution and review of the new Qwen output on Windows are pending. [Local Qwen setup](docs/LOCAL_AI.md) · [Windows evidence](docs/LOCAL_WINDOWS_CHECK.json). [Cobertura, pruebas y pendientes](docs/STATUS.md) · [evidencia de proveedores](docs/LIVE_VALIDATION.json).

**Interfaz:** portada con buscador, horizonte de inversión, empresas recientes, informes y seguimiento; navegación principal en español y adaptación a móvil. [Recorrido y capturas de la primera versión](docs/INTERFACE.md).

## Ejecutar en el entorno cloud/Linux

Requisitos: Node.js 24, Python 3.12, npm y acceso HTTPS a los proveedores/registros.

```bash
cd /workspace/Stock-Analyser
./scripts/install.sh
# Opcional para entorno local: copia .env.example a .env y completa tus valores.
./scripts/start.sh
```

En cloud ya existen las variables de SEC/Finnhub/Alpha Vantage. No copies sus valores a archivos ni los publiques. El supervisor interpreta `.env` como datos, sin ejecutarlo, y respeta las variables ya exportadas. Inicia un solo worker FastAPI (puerto 8000) y Next.js (3000), ambos en loopback. Ctrl+C detiene sus propios procesos. `API_PORT` / `WEB_PORT` permiten aislar instancias. Después de cambiar configuración, reinicia; después de cambiar frontend, recompila.

## Windows, para el siguiente paso local

PowerShell install/start scripts were run successfully by the user on Windows. They require Python 3.12 and Node.js 24:

```powershell
.\scripts\install.ps1
# Crear y configurar .env según .env.example
.\scripts\start.ps1
```

The data and valuation tools work independently of AI. For local research, run LM Studio and this application on the same Windows PC; select `AI_PROVIDER=local` and `LOCAL_AI_MODEL=qwen/qwen3.5-9b`. See [LOCAL_AI.md](docs/LOCAL_AI.md) for the setup and structured-output check. Paid AI remains blocked by default.

## Uso

1. Busca una empresa por nombre o ticker; abre su ficha y verifica precio, fecha, divisa y límites de cobertura.
2. Financial Statements permite anual, trimestral y TTM. Si no hay cuatro trimestres compatibles, se muestra ausencia de cobertura. Pulsa las cifras para consultar fuente y cálculo.
3. Stock Overview permite ratios anuales o TTM, además de ROE/ROA con saldos medios, ROIC contable aproximado, crecimiento y cobertura de datos con fuentes. Los precios se identifican como últimos disponibles, sin garantía de tiempo real. No se mezclan monedas ni se asignan acciones a una clase sin verificación. La cobertura no es una puntuación de inversión.
4. En Valuation Lab importa el último ejercicio, completa los datos que falten y justifica supuestos. Importes en **millones**, tasas en **porcentajes**; la API recibe importes absolutos y tasas decimales. Los supuestos iniciales no son previsiones.
5. Calcula, inspecciona sensibilidad y Reverse DCF y guarda versiones. Cambios sin recalcular se señalan. Una nueva versión conserva padre, diferencias, snapshot y efecto sobre valor.
6. En Scenarios construye casos bajista/base/alcista de cotización a 3/6 meses con EPS forward, P/E y dividendos explícitos, fundamento e invalidación. Calcula precio condicional y retorno, conserva cotización/evidencia y exporta JSON/PDF. Son hipótesis manuales, no pronósticos automáticos. Los escenarios DCF mantienen su sección de valor presente.
7. Elige horizonte (3–6 meses por defecto, o 3/6 meses) e inicia Quick o Deep Research. Ambos cambian la profundidad, no el plazo: recuperación real SEC/Finnhub, progreso, fuentes, documentos leídos, extractos y errores. El horizonte y sus fechas se guardan en el expediente y JSON/PDF. Sin IA se entrega evidencia, sin fingir tesis de analista ni pronósticos.
8. Revisa el informe de 18 apartados: los no evaluados quedan identificados. Exporta JSON, descarga el PDF del servidor o imprime desde el navegador.
9. En Competitors compara empresas o calcula una valoración relativa: selecciona de 2 a 8 pares, justifica similitudes y diferencias, elige múltiplo y base anual/TTM. Revisa exclusiones, mediana, dispersión y sensibilidad; guarda el snapshot y expórtalo. Sin dos pares válidos no se genera valor. La app no certifica comparabilidad económica. También puedes filtrar/ordenar el universo consultado y guardar notas en Watchlist.
10. Quantitative Analysis permite elegir **explícitamente** precios sin ajustar y benchmark opcional (por ejemplo SPY). Los splits/dividendos pueden distorsionar esas métricas. La serie ajustada exige derechos del proveedor y no se sustituye automáticamente.
11. Live Research incluye calendario de resultados de Finnhub, con fechas **estimadas**, y registro de catalizadores con fuente, hipótesis e invalidación. Editar estado/fecha crea otra versión. Los escenarios guardados conservan las versiones vinculadas.

## Configuración y costes

| Proveedor | Variable | Estado / límites |
| --- | --- | --- |
| SEC EDGAR | `SEC_USER_AGENT` con contacto real | Fundamentales y documentos públicos, sin API key. |
| Finnhub | `FINNHUB_API_KEY` | Cotización y noticias/extractos; conexión validada. Cuota y derechos del plan. |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Serie diaria sin ajustar validada; ajustada no disponible en el plan actual. |
| Local AI | `AI_PROVIDER=local`, `LOCAL_AI_BASE_URL`, `LOCAL_AI_MODEL` | LM Studio on the same PC, English structured claims and quote checks. |
| Paid AI | `PAID_AI_ENABLED=false` | Independently blocked. Local errors never trigger a paid fallback. |

No se contrató ningún servicio ni se llamó a una API de IA de pago. La suscripción de ChatGPT no incluye facturación de OpenAI API. El adaptador OpenAI queda como opción técnica futura, desactivado: no es necesario configurar `RESEARCH_API_KEY` para continuar. La interfaz tampoco activa llamadas cuando el backend las tiene bloqueadas.

Nunca introduzcas claves en frontend, Git o chat. `.env` y la base están ignorados. [Referencias oficiales y derechos](docs/PROVIDERS.md).

## Pruebas y verificación real

```bash
./scripts/test.sh
# Proveedores reales configurados; no hace llamadas IA:
PYTHONPATH=backend .venv/bin/python scripts/verify_live.py
# Rentabilidad y comparables con datos reales, sin guardar modelos:
PYTHONPATH=backend .venv/bin/python scripts/verify_analytics.py
# Aplicación ya iniciada, smoke local sin persistir datos ficticios:
PYTHONPATH=backend .venv/bin/python scripts/smoke.py
```

Las pruebas controladas de navegador esperan una instancia con proveedores vacíos y base aislada. Ejemplo Linux, en otra sesión:

```bash
API_PORT=8100 WEB_PORT=3100 BACKEND_URL=http://127.0.0.1:8100 \
DATABASE_URL=sqlite:////tmp/stock-browser-tests.db \
SEC_USER_AGENT='' FINNHUB_API_KEY='' ALPHAVANTAGE_API_KEY='' RESEARCH_API_KEY='' \
AI_PROVIDER=disabled PAID_AI_ENABLED=false ./scripts/start.sh
# Desde frontend:
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npx playwright test workflow.spec.ts
# Integración real contra la instancia principal con credenciales:
RUN_LIVE=1 npx playwright test live.spec.ts
```

Chromium: `/usr/bin/chromium`, `CHROMIUM_PATH` o navegador instalado por Playwright. El test real guarda modelos e investigación sobre datos reales; los porcentajes son hipótesis de validación, no consenso ni recomendación. No activa IA. Datos, fechas y resultados concretos de cada prueba están en los registros.

Validation includes 214 backend tests and 14 controlled Chromium flows. The 3 previously completed live-provider browser flows were not rerun for the latest [research-quality update](docs/RESEARCH_QUALITY.md). [Métricas y comparables](docs/ANALYTICS_VALIDATION.json), [horizontes](docs/HORIZON_VALIDATION.json) y [escenarios/calendario](docs/NEAR_TERM_VALIDATION.json) conservan evidencia. Los supuestos de prueba se identifican expresamente; estas ejecuciones no validan predicciones de cotización.

## Persistencia, arquitectura y seguridad

SQLite `stock.db` guarda modelos, escenarios, trabajos, fuentes, snapshots, notas y caché. Conserva la base al actualizar y haz copias. Hay esquema inicial v1, sin migraciones evolutivas aún. PostgreSQL requiere driver/migraciones y validación pendientes. Dos trabajos concurrentes, ocho en cola, cancelación e interrupción explícita al reiniciar; no hay cola distribuida.

La recuperación limita hosts, redirecciones y tamaños; solo admite la redirección específica del directorio Finnhub hacia su CDN oficial. No ejecuta código o HTML de fuentes externas. Las claves permanecen en servidor. `APP_TOKEN` protege la API interna y es obligatorio en producción; **no es autenticación de usuarios del frontend**. El proxy valida origen en mutaciones. Uso personal local: no exponer a internet sin autenticación y TLS. No hay brokers ni órdenes.

Docker/Compose suministrados con volumen SQLite y puerto limitado a loopback; **no construidos ni probados en contenedores**. Sigue el runtime cloud para proxy/CA sin desactivar TLS.

[Arquitectura](docs/ARCHITECTURE.md) · [Metodología](docs/METHODOLOGY.md) · [Estado detallado](docs/STATUS.md).
