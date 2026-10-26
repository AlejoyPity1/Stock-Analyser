# Metodología financiera

## Horizonte de inversión

El horizonte principal del usuario es **3–6 meses**, para la acción que seleccione en cada ocasión. Una nueva investigación guarda la opción elegida (rango 3–6, 3 o 6 meses), fecha base UTC y fechas futuras por meses naturales. Al sumar meses se ajusta al último día válido si falta el día original. Son fechas de referencia para la investigación, no órdenes ni fechas recomendadas de compra/venta. Se conservan al consultar o exportar el informe más tarde; los informes antiguos sin ese dato permanecen sin horizonte registrado.

Quick/Deep cambian el alcance de recuperación. Las consultas de noticias de 30/90/365 días miran hacia atrás y no determinan el horizonte de inversión. Resultados, guidance, catalizadores, noticias, momentum y riesgos deben evaluarse respecto de la ventana elegida; no se deducen fechas de eventos futuros de las fechas de publicación. Esta orientación no equivale a tener ya evaluados esos apartados. La tesis automática y la generación/evaluación automática de escenarios bursátiles a 3/6 meses siguen pendientes; el motor manual se describe al final.

El DCF proyecta flujos a 5–10 años para estimar valor presente. Sus resultados y escenarios no se interpretan como cotizaciones futuras a 3 o 6 meses.

## Procedencia y períodos

Cada cifra SEC conserva etiqueta, accession, unidad, divisa, inicio/fin del período, fecha de presentación, recuperación y enlace SEC. Se muestran anuales de 300–380 días de 10-K/20-F/40-F y enmiendas admitidas. Se excluyen períodos trimestrales y presentaciones futuras. Las cifras comparativas revisadas se seleccionan por fecha de presentación disponible. No es un sistema histórico point-in-time completo: el snapshot guardado sí conserva lo efectivamente utilizado.

No se mezclan balances de cierre intermedio con ingresos de otro cierre. Las etiquetas IFRS tienen cobertura parcial. Un tag no disponible produce ausencia, nunca cero. La deuda suma componentes específicos y muestra su fórmula; puede faltar deuda de corto plazo, arrendamientos u obligaciones fuera de las etiquetas cubiertas. No se considera deuda a todo el pasivo.

Ratios con precio: último precio disponible / último ejercicio anual por defecto; TTM es una base separada y seleccionable. Capitalización aproximada = precio × acciones diluidas medias del período; no se afirma que sean acciones puntuales actuales. Si divisas difieren, no se calculan múltiplos. No hay conversión FX implícita ni tratamiento automático ADR/acción ordinaria. Los ratios básicos ROE/ROA usan saldo final y así se nombran; el panel de rentabilidad ofrece las versiones con saldos medios descritas abajo. El P/E, earnings yield y ROE requieren beneficio atribuible a propietarios: `ifrs-full:ProfitLoss` total no se presume atribuible al accionista de la matriz. Datos incompletos producen ausencia, nunca cero.

La función TTM probada acepta exactamente cuatro trimestres independientes y contiguos, en la misma moneda. Los flujos se suman, las acciones medias se ponderan por días. La UI ofrece series trimestrales y TTM únicamente cuando se pueden reconstruir con períodos compatibles; véase la metodología ampliada al final.

## DCF FCFF v1.0

Para cada año de 5 a 10:

- Ingresos(t) = ingresos(t−1) × (1 + crecimiento).
- EBIT = ingresos × margen operativo.
- NOPAT = EBIT − max(EBIT, 0) × tipo impositivo. No se presupone devolución fiscal inmediata por pérdidas.
- FCFF = NOPAT + D&A − capex − ΔNWC.
- D&A y capex son ratios de ingresos; ΔNWC = variación de ingresos × ratio NWC.
- Flujo terminal recalculado con crecimiento terminal y su reinversión; no se prolonga la ΔNWC del crecimiento explícito.
- TV = FCFF terminal / (WACC − g).
- EV = suma de flujos descontados + TV descontado; equity = EV − deuda neta.
- Valor por acción = equity / acciones diluidas.
- Upside = valor/precio − 1. Margen de seguridad = 1 − precio/valor, solo con valor positivo.

Importes nominales y una moneda; WACC > g, g terminal entre −5% y 5%, rangos de entrada validados. Son controles matemáticos, **no prueba de sostenibilidad económica**. Se advierte de flujo terminal no positivo, equity negativo o dependencia terminal superior al 80%. No se interpreta un valor negativo como precio objetivo negociable. La sostenibilidad de márgenes, reinversión y crecimiento requiere juicio del usuario.

WACC manual: CAPM × peso de equity + coste de deuda después de impuestos × peso de deuda. No se inventan tasas actuales, beta ni primas de mercado. Sensibilidades WACC/g y crecimiento/margen se calculan en backend; la UI muestra WACC/g.

Reverse DCF busca crecimiento en [−50%, 50%] por bisección y comprueba monotonicidad numérica. Sin solución o con curva no monótona devuelve una explicación. Mantiene el resto de hipótesis constante. No representa un consenso observado.

Escenarios: tres modelos independientes editables con divisa/horizonte común. Son valores presentes. No hay probabilidades ni previsiones bursátiles a un año derivadas automáticamente del DCF.

## Investigación

SEC aporta documentos originales. Finnhub aporta publicaciones relacionadas por el proveedor; su relevancia económica no se presume confirmada. Se conservan título, enlace, publicador, fechas y estado. Se consulta 30 días en Quick y 30/90/365 en Deep, con máximo configurable y sin rellenar con artículos ficticios. Duplicados por URL canónica; no se detectan todavía republicaciones semánticas.

Documentos SEC: lectura de hasta 120.000 caracteres y hash del documento recuperado. Textos más largos se etiquetan truncados. Noticias: solo extracto autorizado del proveedor. No se afirma haber leído el artículo del editor. Los números encontrados, únicos, seleccionados, leídos, inaccesibles y utilizados por la IA son distintos. La relevancia confirmada permanece sin evaluar.

El adaptador IA, actualmente desactivado y pendiente de sustitución/integración local, exige hechos reportados, inferencias e hipótesis con cita literal. Se valida estructura, ID de fuente y texto citado. No se certifica automáticamente que la cita respalde toda la interpretación. Tesis y contradicciones siguen siendo análisis del sistema por revisar. Ninguna cifra de la IA alimenta el motor financiero.

Cambios: el usuario edita hipótesis, elige fuente, justifica y guarda una versión con padre. Se conservan valor anterior, nuevo y efecto en valor. La mera existencia de una noticia no altera los flujos; el usuario debe comprobar calendario, márgenes, reinversión, escenarios y doble contabilización.

## Cuantitativo

Serie ajustada por el proveedor o sin ajustar elegida explícitamente. Rendimiento entre extremos, volatilidad de retornos diarios con desviación muestral × √252, drawdown sobre máximo acumulado, SMA50/SMA200 solo con datos suficientes, RSI14 Wilder. Beta y correlación requieren un benchmark real compatible y sesiones alineadas, como se describe abajo. El retorno total reinvertido certificado y la comparación sectorial permanecen pendientes.

## Actualización: trimestres, divisa de cotización e histórico sin ajustar

La base anual sigue siendo predeterminada. Hay series trimestrales separadas: valores directos de 70–110 días o diferencia entre acumulados con idéntico inicio fiscal. Q4 se obtiene de FY menos nueve meses cuando existen ambos. El cálculo conserva los dos componentes; no se reparte un año arbitrariamente. Las acciones diluidas trimestrales se derivan ponderando los días de los acumulados. El EPS diluido no se deriva por resta.

TTM se construye solo con cuatro trimestres independientes y contiguos, en la misma divisa. Se suman flujos, se ponderan acciones y se toma el balance del último cierre. Si falta un trimestre, el TTM no se publica. Las fuentes y cálculos se muestran en Financial Statements; los ratios permiten elegir anual o TTM. Actualmente GPRK/ASML no tienen la cobertura trimestral necesaria en los hechos XBRL recuperados.

La moneda de perfil corporativo de Finnhub puede ser la de reporte y no la del precio. La cotización usa la moneda del instrumento exacto en el directorio US del proveedor. ASML: precio US en USD, estados en EUR. Sin una conversión explícita verificable no se calculan múltiplos ni upside cruzando esas monedas. Las variantes de símbolo de clase con guion/punto se resuelven contra ese directorio, sin sustitución ciega. Si el emisor tiene varias clases cotizadas y no se ha verificado la atribución de acciones, se bloquean los múltiplos; el DCF exige acciones de la clase introducidas y justificadas manualmente.

El histórico sin ajustar es una elección explícita del usuario, nunca un fallback a la serie ajustada. Se etiqueta como tal en datos, gráfico y metodología. Sus retornos pueden quedar distorsionados por splits y dividendos. La comparación con benchmark exige divisa de negociación verificada común y al menos 21 sesiones coincidentes. Se alinean fechas antes de calcular retornos; beta = covarianza muestral / varianza muestral del benchmark. Con varianza nula no se inventa beta/correlación. La rentabilidad relativa es (1+retorno acción)/(1+retorno benchmark)−1. No es retorno total certificado ni indicador predictivo.

El PDF autónomo se construye con los datos guardados y marca apartados sin evaluación cualitativa. Puede contener gráficos de FCFF de los modelos vinculados. La existencia de 18 apartados no equivale a completar sus investigaciones.

## Rentabilidad anual y cobertura · fundamentals-1.0

ROE = beneficio atribuible a propietarios / patrimonio de propietarios medio. ROA = resultado neto reportado / activos medios; es una aproximación contable, con posibles partidas no operativas. Media = (saldo inicial + saldo final) / 2, con dos cierres consecutivos separados 300–380 días y saldos positivos. No es una media diaria. Un ROE alto puede proceder de recompras o apalancamiento.

ROIC aproximado = NOPAT proxy / capital invertido medio. NOPAT proxy = EBIT − max(EBIT, 0) × (gasto fiscal / resultado antes de impuestos). Capital invertido = patrimonio total + deuda − efectivo. Se usa patrimonio total reportado o, si falta, activos − pasivos, conservando la derivación. El cálculo exige capital positivo en ambos cierres, beneficio antes de impuestos positivo y tasa efectiva de 0% a 100%. Una tasa fuera de ese rango no se sustituye por una normalizada. No se aplica este ROIC industrial a entidades financieras SIC 6000–6999.

El ROIC usa todo el efectivo y una tasa fiscal corporativa como aproximación operativa. No normaliza efectivo excedentario, goodwill, I+D, partidas extraordinarias ni arrendamientos ausentes de la deuda cubierta. Por eso se identifica como aproximado. Los hechos con moneda, cierre, duración de flujo o publicación incompatible se excluyen antes de calcular. El CAGR de cinco ejercicios exige seis cierres consecutivos, ingresos positivos y extremos compatibles; no es una previsión.

La cobertura cuenta presencia de 20 campos definidos y muestra ausencias, fuentes incompletas, antigüedad, trimestres y TTM. No certifica calidad empresarial ni auditoría. El balance se comprueba contra patrimonio total reportado independiente; si el patrimonio procede de activos − pasivos, no se presenta esa identidad como una comprobación. Tolerancia de redondeo = max(1 unidad monetaria, 0,001% de activos).

Para múltiplos con precio se exige cotización de hasta 7 días, ejercicio anual de hasta 550 días o TTM de hasta 200 días, sin fechas futuras (se toleran 5 minutos de desfase del reloj de cotización). Los ratios históricos sin precio permanecen identificados como tales.

## Valoración relativa condicional · relative-1.0

El usuario selecciona de 2 a 8 pares y justifica negocio, crecimiento, márgenes y riesgos. Coincidir en sector o superar controles de datos no certifica comparabilidad económica. Se requiere objetivo válido y al menos dos pares válidos, misma moneda de reporte y precio compatible, cierres separados hasta 92 días, cotizaciones recientes, acciones diluidas medias positivas y procedencia de cada input necesario. Se excluyen múltiplos no positivos o no calculables; no se usa beneficio negativo para generar un P/E. Entidades financieras requieren métodos sectoriales para múltiplos distintos de P/E.

P/E utiliza beneficio atribuible a propietarios; P/FCF utiliza OCF − capex; EV/EBITDA utiliza EBIT + D&A; EV/Revenue utiliza ingresos. Se muestra mediana, mínimo/máximo y percentiles 25/75 por interpolación lineal, sin eliminación automática de outliers. Con menos de cinco pares se advierte del tamaño de la muestra.

Equity implícito = mediana × fundamental del objetivo, menos deuda neta solo para múltiplos EV. Valor por acción = equity implícito / acciones diluidas medias. La sensibilidad aplica los múltiplos de la distribución al mismo fundamental. El upside solo se publica si el equity implícito es positivo. No hay consenso forward ni ajuste automático por ciclo, márgenes o estructura de capital. Es un valor condicional a la elección de pares, sin interpretación de predicción o recomendación.

Se guardan justificación, método, base financiera, hechos de cada período, cotización, fuentes, exclusiones y resultados. Un informe incorpora modelos existentes al iniciar la investigación o vinculados después al mismo expediente; conserva las entradas originales.

## Escenarios de cotización · price-horizon-1.0

Cada horizonte (3 o 6 meses naturales desde el cálculo) contiene casos bajista, base y alcista independientes. El usuario introduce EPS forward de los **12 meses siguientes a la fecha objetivo**, P/E supuesto y dividendos por acción durante el horizonte. No se prorratea el EPS anual. Las hipótesis deben corresponder al mismo instrumento/ADR, clase y moneda del precio. La API exige cotización positiva de hasta 7 días y moneda verificada compatible; la atribución económica del EPS manual depende del supuesto documentado.

Precio condicional = EPS forward × P/E. Retorno de precio = precio condicional / precio inicial − 1. Retorno bruto con dividendos = (precio condicional + dividendos hipotéticos) / precio inicial − 1, sin reinversión, impuestos, comisiones ni ajuste automático por splits. Cero dividendos debe indicarse explícitamente. P/E de equilibrio = (precio inicial − dividendos) / EPS, no publicado si resulta negativo. Este método exige EPS y P/E positivos; empresas en pérdidas necesitan otro modelo, pendiente.

Se exige orden bajista ≤ base ≤ alcista tanto en precio como en retorno con dividendos. Beneficio/riesgo = retorno alcista / pérdida absoluta bajista solo cuando el bajista pierde y el alcista gana. Es comparación de hipótesis, no probabilidad ni expectativa estadística. No se asignan probabilidades ni se interpola un horizonte a partir del otro.

Cada caso conserva fundamento e invalidación; el modelo guarda cotización y snapshots de catalizadores. No suma automáticamente noticias al EPS. Dos versiones de un evento no se pueden vincular como eventos distintos; esto evita duplicación literal de versiones, sin garantizar ausencia de doble contabilización económica entre hipótesis diferentes. Calcular o guardar recupera el precio disponible y ancla las fechas a esa ejecución; abrir una versión guardada no las recalcula. Una investigación vinculada exige mismo ticker y horizonte, mostrando las fechas de cada modelo por separado.

## Calendario y registro de catalizadores

Finnhub devuelve fechas de resultados para el instrumento y ventana de seis meses. Se filtran identidad, fechas y duplicados exactos. Son estimaciones pendientes de confirmación oficial; una lista vacía no prueba ausencia de eventos. No se contrata otro plan ni se sustituyen accesos denegados por fechas inventadas.

El registro admite fechas desconocidas, estimadas o reportadas por el usuario, fuente, cita, hipótesis, invalidación y estado previsto/ocurrido/cancelado. Una referencia externa no implica lectura del editor. Si la fuente pertenece a un expediente de la misma empresa con contenido recuperado, se comprueba coincidencia literal de la cita; eso no certifica la interpretación de su fecha o impacto.

Editar crea un UUID nuevo conservando el ID del evento y la versión anterior. El listado muestra la última versión dentro de los 1.000 registros recientes por empresa. Los modelos retienen el estado elegido entonces. El informe incluye versiones capturadas al investigar o vinculadas después; una revisión ajena no reemplaza su evidencia. La clasificación distingue pasado, dentro/fuera del horizonte, desconocido y cancelado; la fecha de publicación no se interpreta como fecha del evento.
