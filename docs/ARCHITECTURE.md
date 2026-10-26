# Arquitectura

```
Browser → Next.js /api proxy → FastAPI → adapters SEC / Finnhub / Alpha Vantage
                                     → research → OpenAI Responses (opt-in)
                                     → deterministic finance
                                     → SQLAlchemy → SQLite
```

- `backend/app/providers.py`: interfaz de mercado, normalización SEC, transporte HTTPS, límites por host, reintentos transitorios, caché y procedencia. Destinos limitados a lista fija; solo sigue la redirección específica del directorio Finnhub a su CDN oficial. No intenta evadir bloqueos.
- `finance.py`: FCFF, escenarios, sensibilidad, Reverse DCF, ratios, TTM estricto, WACC CAPM, indicadores de precios.
- `research.py`: cola asíncrona local acotada, ventanas de consulta, deduplicación por URL canónica, lectura SEC, estadísticas, síntesis estructurada y validación de citas. Persistencia de estados reales. Sin crawler web general.
- `store.py`: registros inmutables de modelos por UUID, fuentes y progreso de trabajos, snapshots actuales, caché con expiración. Inicialización SQLAlchemy v1.
- `main.py`: API, validación, control de acceso del servidor, rate limit, watchlist, comparación, screener y exportación de expedientes.
- `frontend/app/page.tsx`: workspace con doce secciones; formularios y vistas conectados a la API. CSS propio responsive, Lucide y Recharts. Se omitieron Tailwind, shadcn y Lightweight Charts para reducir dependencias; la gráfica ajustada usa Recharts.
- `frontend/app/api/[...path]/route.ts`: proxy del servidor; URL y token solo server-side. Sin CORS abierto ni claves públicas.

API principal: `/search`, `/companies/{symbol}`, `/companies/{symbol}/history`, `/valuation/preview`, `/valuations`, `/scenarios`, `/relative`, `/relative-analysis`, `/relative-valuations`, `/research`, `/research/{id}/cancel`, `/records`, `/records/{id}`, `/reports/{id}`, `/watchlist`, `/compare`, `/screen`, `/settings`, `/health`.

Los documentos de un trabajo se conservan con texto/hash y estado de lectura. La investigación conserva su instantánea financiera y cotización de ese momento. Un informe exporta ese snapshot y las valoraciones existentes al iniciar o vinculadas después mediante investigación. No reemplaza una fuente antigua por un dato nuevo sin identificarlo.

`/relative` conserva el cálculo con inputs manuales. `/relative-analysis` obtiene snapshots de un grupo de tickers elegido y justificado por el usuario, comprueba admisión y calcula una mediana descriptiva. `/relative-valuations` guarda el modelo únicamente con objetivo y al menos dos pares válidos. La UI muestra bases, diferencias y exclusiones; no presume comparabilidad económica.

Límites operativos: un proceso backend, caché local por entorno, base personal sin aislamiento multiusuario. Una cola duradera externa, migraciones evolutivas, usuarios y workers distribuidos son trabajo futuro, no capacidades declaradas.

## Ampliación v0.2

- `periods.py`: trimestres directos/derivados y TTM estricto, con componentes de origen.
- `reporting.py`: estructura de 18 apartados, estados de disponibilidad y renderizado PDF autónomo con ReportLab. Las entradas externas se escapan antes de incluirlas en párrafos PDF.
- `/scenario-sets`: persistencia de escenarios con una misma base financiera y vínculo opcional a investigación. `/records?kind=scenario` recupera historial.
- `/reports/{id}/pdf`: descarga binaria a través del proxy Next.js, que conserva Content-Type y Content-Disposition.
- `/companies/{symbol}/history?adjusted=false&benchmark=SPY`: elección explícita de serie y benchmark; sin compra automática de planes.
- `/screen`: crecimiento, deuda/EBITDA, industria, país, capitalización con divisa explícita y ordenación. Los valores ausentes se excluyen del filtro y quedan al final de la ordenación.
- Componentes frontend separados para estados, ratios e informe estructurado.
- El endpoint `/research` es asíncrono: crea tareas en el loop de la aplicación, no en un thread de handlers síncronos.
- La inicialización de esquema y la recuperación de tareas se separaron: ejecutar verificaciones de proveedores no interrumpe trabajos de otro proceso activo.
- `PAID_AI_ENABLED=false` bloquea cualquier llamada pagada aunque exista una clave. The local LM Studio connector is separately selected with AI_PROVIDER=local and never falls back to a paid provider. No se considera habilitado el modelo por tener un valor en RESEARCH_MODEL.
- Supervisor probado en Linux y con puertos configurables para pruebas aisladas. Rama Windows y wrappers PowerShell suministrados, pendientes de ejecutar en Windows.

## Rentabilidad, calidad de datos y comparables

- `analytics.py`: metodología `fundamentals-1.0`; saldos medios para ROE/ROA, ROIC industrial aproximado, crecimiento y cobertura. Filtra incompatibilidades antes de calcular y conserva fórmulas, inputs y motivos de ausencia. No genera un score de inversión.
- `comparables.py`: metodología `relative-1.0`; validación de grupo, selección anual/TTM, checks de moneda/fechas/procedencia, distribución y puente EV/equity. El motor no selecciona ni certifica los pares.
- `/companies/{symbol}` añade `analytics`. Los múltiplos con precio requieren antigüedad compatible; el snapshot mantiene ratios históricos sin precio cuando corresponda.
- Los modelos relativos se guardan como registros `relative`. La investigación captura sus IDs al iniciar; los añadidos después pueden vincularse con `research_id`. JSON/PDF incluyen entradas y limitaciones originales.
- `FundamentalAnalytics.tsx` y `RelativeValuation.tsx`: componentes de rentabilidad/cobertura y cálculo/historial de comparables. No requieren un modelo IA.
- `scripts/verify_analytics.py`: evidencia real de métricas y comparables, sin llamadas IA ni modelos nuevos guardados; utiliza la caché normal del proveedor y no interrumpe trabajos.

## Horizonte de investigación

- `horizon.py`: contexto de inversión con meses naturales y fecha base UTC. Rango 3–6 meses predeterminado, opciones 3/6. No calcula una previsión de precio.
- `POST /research`: campo `horizon` validado (`3-6m`, `3m`, `6m`). El trabajo registra el contexto al encolarse y lo conserva al completarse o fallar. El prompt del adaptador IA recibe ese horizonte; no se activa IA por añadirlo.
- `investment_horizon` se conserva en la investigación y se exporta en el informe `evidence-2.1` y PDF. La exportación no recalcula las fechas. Un expediente antiguo sin contexto permanece sin horizonte.
- `HorizonSummary.tsx`: contexto visible en investigación e informe. La selección actual del formulario no altera un trabajo ya guardado.
- Los símbolos se resuelven por los adaptadores existentes. No hay una whitelist de empresas de demostración; la cobertura sí está limitada por los proveedores actuales, descritos en `PRODUCT_SCOPE.md`.

## Escenarios de precio y catalizadores

- `near_term.py`: Pydantic y cálculo puro `price-horizon-1.0`, EPS forward × P/E a 3/6 meses. Retornos de precio/dividendos, equilibrio y relación condicional beneficio/riesgo. Cotización/moneda verificadas, casos ordenados, números finitos, fundamento e invalidación obligatorios.
- `/price-scenarios/preview` y `/price-scenarios`: el backend obtiene el precio real; no acepta una cotización del cliente. Guarda registros `price_scenario`, snapshots de catalizadores y vínculo opcional al expediente del mismo ticker/horizonte.
- `catalysts.py`: referencias externas o citas de fuentes leídas; registros `catalyst` con ID estable de evento y versiones inmutables. `/catalysts` lista últimas versiones por empresa o guarda una revisión. No descarga URLs introducidas por el usuario.
- `/companies/{symbol}/earnings-calendar`: calendario Finnhub de seis meses, identidad exacta y fechas filtradas. Son estimaciones sin confirmación oficial.
- `PriceScenarios.tsx` y `CatalystBoard.tsx`: formularios con supuestos vacíos, evidencia y versiones. Guardar vuelve a recuperar la cotización y muestra su referencia.
- La investigación captura IDs de modelos y catalizadores. El informe `evidence-2.2` incorpora los vinculados y añade anexo PDF con supuestos/resultados, conservando los snapshots. No se confunde con los escenarios FCFF.


## Local AI connector

- `local_ai.py`: same-machine loopback endpoint validation, exact model check, serialized GPU requests, conservative context budgets, deterministic evidence windows and per-batch citation validation.
- `synthesis.py`: shared output schema, English system instructions, literal quote matching against supplied excerpts, and deterministic formatting of checked claims.
- `AI_PROVIDER=disabled|local|openai`: explicit routing. Paid mode additionally requires its own authorization/configuration; local failure does not change provider.
- `POST /settings/local-ai/check`: configured model ID listing only; no inference or GPU-success claim.
- `scripts/verify_local_ai.py`: synthetic schema/quotation check run on the Windows PC; no database fixtures or paid API calls.
- Report `evidence-2.3`: preserves local model/provider, excerpt coverage/omissions and an AI claim/quotation annex in PDF.

[LOCAL_AI.md](LOCAL_AI.md) describes implementation limits and validation still needed on Windows.
