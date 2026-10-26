# Primera versión de la interfaz

La interfaz está conectada a la aplicación existente. Diseño oscuro en grafito y verde suave, navegación principal en español y prioridad al horizonte de 3–6 meses.

## Recorrido

1. **Inicio:** búsqueda libre por empresa o ticker; ejemplos opcionales. Selector de 3–6, 3 o 6 meses para la próxima investigación. Actividad guardada, empresas recientes, expedientes y seguimiento. Las cotizaciones del historial se etiquetan como precios guardados y muestran la fecha de la cotización.
2. **Resumen de la empresa:** datos disponibles, fundamentales, seguimiento y accesos a investigación rápida/profunda o escenarios. Una barra enlaza empresa → investigación → escenarios → informe.
3. **Investigación y escenarios:** conservan los motores existentes, sus fuentes, supuestos, versiones e invalidaciones. La portada transmite el horizonte elegido a la investigación; los expedientes guardados conservan su horizonte original.
4. **Informes:** se pueden retomar desde Inicio o seleccionar en la sección de informes. El encabezado muestra el símbolo del expediente abierto, incluso si se había consultado otra empresa.

Estados financieros, DCF, comparables y exploración quedan agrupados como herramientas. Precio y riesgo, informes y seguimiento mantienen sus funciones. La IA local aparece como pendiente de integración.

## Interacción y accesibilidad

- Búsqueda con `Ctrl+K` o `⌘K`; resultados en diálogo nativo con selección mediante flechas, Enter y cierre con Escape. Recupera el foco al cerrar y muestra los errores del proveedor dentro del diálogo.
- Menú móvil con fondo superpuesto, bloqueo del contenido, foco contenido en el menú y cierre con Escape o botón. En pantallas de más de 760 px se usa navegación lateral.
- Enlace para saltar al contenido, foco visible, etiquetas de controles, estado de navegación y respeto a movimiento reducido.
- Layout revisado en escritorio, tableta y móvil; tarjetas financieras en una columna en pantallas de hasta 360 px para conservar importes legibles.
- Estados de carga, error y falta de datos; los contadores no muestran ceros ficticios durante una carga fallida. Las empresas se deduplican por ticker en la portada.

## Archivos

- `frontend/components/WorkspaceHome.tsx`: portada y actividad.
- `frontend/components/SearchResults.tsx`: búsqueda y navegación por teclado.
- `frontend/components/workspace.ts`: etiquetas de navegación, horizontes y estados.
- `frontend/app/page.tsx`: integración con los flujos existentes, menú y recorrido.
- `frontend/app/workspace.css`: apariencia de la interfaz y adaptaciones responsive; las tablas y componentes financieros conservan los estilos base de `globals.css`.

## Verificación

Compilación de producción y TypeScript; 12 pruebas Chromium controladas y 3 flujos con proveedores reales. Incluyen DCF, escenarios, catalizadores, persistencia, JSON/PDF, selección de horizonte, búsqueda por teclado y menú móvil. El flujo real de AAPL también comprueba ausencia de desbordamiento a 320 px. No hubo llamadas de IA de pago.

Las pruebas controladas usan una base aislada y fixtures identificados. Las de integración guardan hipótesis expresamente marcadas como validación; no son previsiones ni recomendaciones. La comprobación visual y de teclado no equivale a una auditoría exhaustiva de accesibilidad.

Capturas de esta versión: [escritorio](images/interface-desktop.png) · [móvil](images/interface-mobile.png). Muestran la instancia con su historial de validación. No hay datos de mercado simulados en la portada.
