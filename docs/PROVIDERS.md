# Proveedores y estado verificado

| Proveedor | Referencia oficial | Resultado actual |
| --- | --- | --- |
| SEC EDGAR | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | Fundamentales y documentos de AAPL/GPRK/ASML recuperados. Ingresos contrastados con iXBRL del informe anual. |
| SEC fair access | https://www.sec.gov/about/developer-resources | Identificación por SEC_USER_AGENT con contacto; espaciado >1 s por host. |
| Finnhub | https://finnhub.io/docs/api | Clave existente validada para cotización, directorio de instrumentos y noticias. Extractos, no lectura del artículo original. |
| Alpha Vantage | https://www.alphavantage.co/documentation/ | Serie diaria sin ajustar disponible; serie ajustada restringida al plan premium. No se compró un plan. |
| OpenAI | https://platform.openai.com/docs/api-reference/responses | Adaptador desactivado por defecto. Ninguna llamada pagada. No requerido para continuar. |

Evidencia con fechas y fuentes: [LIVE_VALIDATION.json](LIVE_VALIDATION.json). La configuración de red cambió durante el trabajo: los primeros 403 no describen ya el acceso actual a SEC/Finnhub. La documentación pública de Alpha Vantage devolvió 403 en una comprobación, pero su endpoint JSON devuelve la serie diaria solicitada; son operaciones distintas.

No se afirma acceso a Reuters, Bloomberg, FT, estimaciones licenciadas, buscadores ni texto completo de noticias de pago. No se eluden paywalls ni se redistribuye contenido obtenido sin autorización. El usuario debe revisar los derechos de su cuenta antes de un uso distinto al personal; no se han certificado condiciones comerciales completas.

Las divisas de precio se verifican con el instrumento US de Finnhub, no con la moneda de reporte del perfil. El directorio redirige hacia `static2.finnhub.io`; la recuperación permite únicamente esa redirección acotada y no imprime ni guarda su URL firmada en informes/logs. Las credenciales solo se envían a destinos configurados. Las claves no se devuelven al frontend.

Variables backend: `SEC_USER_AGENT`, `FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`. `RESEARCH_API_KEY` queda como alias opcional para la API OpenAI, sin configurar y sin necesidad para el flujo actual. `PAID_AI_ENABLED=false` bloquea las llamadas aunque se introdujera una clave accidentalmente. La suscripción ChatGPT no se usa como credencial de backend. La IA local del ordenador Windows del usuario se deja para el final; no se descargó ni validó ningún modelo.

Calendario de resultados: [Finnhub Earnings Calendar](https://finnhub.io/docs/api/earnings-calendar), consultado por símbolo exacto y ventana de fechas. En la comprobación real NVDA devolvió dos fechas estimadas sin contratar otro plan. No supone confirmación oficial ni cobertura futura garantizada. Si el acceso o los datos faltan, se muestra ausencia/error y sigue disponible el registro manual de referencias.
