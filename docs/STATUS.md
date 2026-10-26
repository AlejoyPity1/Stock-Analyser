# Estado de implementación

Local AI integration is now underway. The LM Studio connector uses `qwen/qwen3.5-9b`, structured English claims, bounded source excerpts and literal quote checks. The user completed a small chat grounding check; real structured inference through this connector, GPU performance and broader financial quality remain pending on Windows. See [LOCAL_AI.md](LOCAL_AI.md) and [the user-reported chat check](LOCAL_MODEL_CHAT_CHECK.json). Paid AI remains independently blocked by default (`PAID_AI_ENABLED=false`); local failures never switch providers.

**Prioridad del usuario:** análisis de la acción que pida en cada ocasión para **3–6 meses**. DCF como contexto de valor presente; noticias, resultados, catalizadores y riesgo de precio como foco del producto. Véase [PRODUCT_SCOPE.md](PRODUCT_SCOPE.md). El objetivo no implica que el pronóstico o la tesis automática ya estén implementados.

## Validación real completada

Fecha y evidencia reproducible: [LIVE_VALIDATION.json](LIVE_VALIDATION.json), generado con `scripts/verify_live.py`.

- **AAPL:** 10 ejercicios anuales; trimestres y TTM hasta 2026-06-27. Ingresos anuales contrastados con el hecho iXBRL del 10-K, mismo contexto fiscal, sin dimensiones de segmento.
- **GPRK:** 10 ejercicios IFRS, ingresos contrastados con el 20-F. Se corrigió la selección de taxonomía: unos pocos tags US GAAP no deben ocultar los estados IFRS.
- **ASML:** 10 ejercicios con estados en EUR; cotización US en USD, verificada con el directorio de instrumentos de Finnhub. Ingresos contrastados con el informe anual. Los múltiplos no se calculan mezclando estas monedas.
- Cotizaciones y noticias recuperadas para las tres empresas. Se distinguen extractos, lectura completa y lectura truncada. No se garantiza tiempo real.
- Histórico **sin ajustar** de AAPL y benchmark SPY: 100 sesiones, 99 retornos alineados; beta, correlación y rendimiento relativo calculados con datos reales. La serie ajustada no está incluida en el plan disponible y no se sustituye silenciosamente.
- Deep Research real de GPRK: 30 fuentes seleccionadas, 5 documentos consultados (4 completos, 1 truncado), 25 extractos, 0 inaccesibles y 0 llamadas IA. Son datos de esta ejecución, no una cobertura garantizada futura.
- Flujo completo real en Chromium: AAPL → estados/TTM → DCF guardado → escenarios guardados → investigación → PDF descargado mediante el proxy.
- Rentabilidad y comparables: [ANALYTICS_VALIDATION.json](ANALYTICS_VALIDATION.json), reproducible con `scripts/verify_analytics.py`. ROE/ROA con dos cierres y ROIC aproximado calculados con inputs SEC trazables para AAPL/GPRK/ASML. GPRK no recibe ROIC porque la tasa fiscal observada no es interpretable según el método.
- Valoración relativa real MSFT con ADP/INTU: bases USD, cierres compatibles, mediana, valor implícito y restauración del snapshot guardado comprobados en Chromium. Grupo de validación técnica, no certificación de comparabilidad económica. ORCL se excluyó en esta ejecución por atribución de acciones a la clase no verificada.
- Horizonte verificado en Chromium con datos reales: AAPL (3–6 meses por defecto) y NVDA escrito en el buscador (3 meses elegidos). El informe conserva el contexto original. [HORIZON_VALIDATION.json](HORIZON_VALIDATION.json) documenta la ejecución; no valida una previsión bursátil.
- Escenarios de cotización NVDA guardados con precio real, EPS/P/E/dividendos de validación explícitos, informe vinculado y PDF descargado. Calendario real Finnhub devolvió dos fechas **estimadas**; no se afirma confirmación oficial. [NEAR_TERM_VALIDATION.json](NEAR_TERM_VALIDATION.json) conserva la evidencia. No es una validación predictiva.

## Capacidades disponibles

- Frontend Next.js/TypeScript y FastAPI integrados, doce secciones responsive.
- Local LM Studio connector, same-PC loopback API, exact model ID, English schema-constrained evidence batches, quotation rejection, context/coverage audit, Settings connectivity check and JSON/PDF preservation. The connectivity check does not certify inference or GPU use.
- Primera versión de interfaz visual: portada con búsqueda libre y horizonte, actividad real guardada, navegación agrupada en español, recorrido empresa → investigación → escenarios → informe, diálogo de búsqueda por teclado y menú móvil accesible. [Alcance y capturas](INTERFACE.md).
- Búsqueda por nombre/ticker SEC; adaptadores sustituibles y errores explícitos.
- Estados anuales, trimestres directos o derivados de YTD y TTM solo con cuatro trimestres contiguos. El EPS diluido no se deriva por resta. Cada valor conserva fuente, período, publicación, unidad y fórmula/componentes cuando se deriva.
- Ratios anuales/TTM seleccionables, FCF, deuda neta, márgenes y múltiplos condicionados a datos y divisas compatibles. Acciones medias, no acciones puntuales actuales. Varias clases cotizadas: se desactivan múltiplos si no hay asignación fiable de acciones a la clase.
- ROE/ROA con media de dos cierres, ROIC industrial aproximado con tasa efectiva observada y capital medio, crecimiento anual y CAGR de cinco ejercicios. Inputs, fórmulas y ausencias explícitos. Se excluyen datos con moneda, duración o cronología incompatibles. El P/E usa beneficio atribuible a propietarios cuando se distingue del resultado total del grupo.
- Cobertura de 20 campos, procedencia, antigüedad y comprobación independiente del balance solo con patrimonio total reportado. No es un score de inversión. Cotizaciones de más de 7 días y estados de más de 550 días (anual) / 200 días (TTM) bloquean sus múltiplos.
- Valoración relativa guardada con 2–8 pares elegidos y justificados, P/E, EV/EBITDA, EV/Revenue o P/FCF. Admisión por datos, moneda y períodos; mediana, dispersión, sensibilidad y puente EV/equity. JSON/PDF conservan el modelo vinculado. Sin dos pares válidos no se calcula valor; no hay selección automática ni certificación económica de pares.
- DCF FCFF 5–10 años, CAPM/WACC manual, valor terminal y reinversión, EV/equity, dilución, upside, margen de seguridad, Reverse DCF y sensibilidades. Inputs iniciales son hipótesis editables. Datos ausentes al importar no se rellenan con supuestos silenciosos.
- Versiones de valoración, diferencias, justificación, noticia asociada y efecto sobre valor. Se conserva el snapshot de partida.
- Escenarios Bear/Base/Bull calculados y guardados, historial y vinculación a un expediente. Las bases financieras iniciales deben coincidir.
- Escenarios de cotización a 3/6 meses por EPS forward × P/E manual, dividendo explícito, fundamento e invalidación. Precio condicional, retornos y relación condicional beneficio/riesgo, con cotización/divisa verificadas. Historial, JSON y anexo PDF; los supuestos no se presentan como consenso ni previsiones del sistema.
- Calendario de resultados estimados de Finnhub por ticker, y registro manual de catalizadores con fuentes/citas, hipótesis, fechas/estado e invalidación. Revisiones inmutables; una edición antigua no puede reemplazar una más reciente. Los modelos conservan la versión elegida y rechazan duplicar versiones del mismo evento. La verificación literal de citas no certifica su interpretación.
- Investigación Quick/Deep con SEC y Finnhub, estados persistidos, cola local acotada, cancelación y señal de interrupción tras reiniciar. Se corrigió y probó el arranque de tareas a través del endpoint asíncrono real.
- Horizonte 3–6 meses por defecto, con opciones 3/6 meses. Se conserva fecha base y ventana por meses naturales desde el inicio del trabajo, incluso al exportar después. JSON/PDF mantienen ese contexto. Informes antiguos no reciben un horizonte inventado. Quick/Deep indican profundidad y las ventanas de noticias son retrospectivas.
- Comparador y screener sobre hasta 100 snapshots recientes: margen, P/E, FCF yield, crecimiento, deuda/EBITDA, industria, capitalización/divisa y país; ordenación con ausentes al final. No se afirma cobertura de todo el mercado.
- Histórico ajustado o sin ajustar elegido explícitamente; retorno, volatilidad, drawdown, medias, RSI y comparación con benchmark alineada por fecha y misma divisa verificada.
- Watchlist y notas persistentes.
- Expediente estructurado de 18 apartados con estados disponible/parcial/pendiente. Export JSON y **PDF autónomo del servidor**, además de impresión del navegador. Un apartado presente no implica que su análisis esté completado.
- SQLite, esquema inicial versionado, caché, backoff, límites por host/solicitudes, validación, claves en backend, proxy con control de origen y token interno.
- Locks reproducibles, scripts Linux, scripts PowerShell propuestos para Windows y Docker/Compose. Estos dos últimos no se han ejecutado en Windows/contenedores.

## Pruebas

- 185 pruebas controladas de backend, incluidas finanzas/períodos, horizontes, escenarios de precio/retornos, catalizadores/versiones, citas, calendario filtrado, persistencia/PDF y bloqueo de IA pagada.
- 13 pruebas Chromium controladas y 3 pruebas Chromium de integración real opt-in. Los tests con fixtures no se confunden con validación externa.
- Build Next.js, TypeScript y comprobación de arranque. Una advertencia de deprecación del cliente de pruebas Starlette/httpx permanece; las pruebas ejecutan y pasan.
- Docker, PowerShell en Windows y GitHub Actions: suministrados, **no validados en esas plataformas**.

## Trabajo pendiente

- Run and evaluate the new local connector on Windows: structured inference, GPU speed, extraction fidelity, semantic comparison and broader thesis quality. A bounded quoted-claim synthesis is implemented; comprehensive qualitative conclusions and semantic retrieval remain pending.
- Búsqueda web general multifuente, filiales/productos/competidores, lectura autorizada de medios originales y deduplicación semántica.
- Cuantificación automatizada de noticias y comprobación de doble contabilización; hoy el usuario justifica los cambios y quedan auditados.
- Cobertura trimestral de emisores extranjeros cuando SEC no ofrece esos hechos; GPRK y ASML no permiten construir TTM con la cobertura XBRL recuperada. No se inventan trimestres.
- FX/ADR, acciones puntuales actuales y mapeo completo de clases; normalización económica de ROIC (efectivo excedentario, goodwill, I+D, arrendamientos), modelos sectoriales, selección fundamentada de pares, múltiplos históricos point-in-time y previsiones externas licenciadas.
- Scoring 0–100 normalizado por sector con cohortes defendibles; no se muestran puntuaciones arbitrarias.
- Automatización y evaluación de escenarios a **3/6 meses**, extracción/confirmación de catalizadores e invalidación, seguimiento contra resultados reales, ajustes corporativos y modelos alternativos para EPS negativo. El motor y registro actuales requieren hipótesis/revisión manual; no son pronósticos validados. Objetivos a 1/3/5 años quedan como extensión secundaria; retorno total reinvertido certificado pendiente.
- Universo de screening amplio, alertas, usuarios, autenticación del frontend, migraciones evolutivas, PostgreSQL y cola distribuida.

La aplicación es un workspace personal local, no un servicio público listo para producción. No se declara completada la especificación integral.
