"use client";
import { pct, num } from "./api";
export default function FundamentalAnalytics({
  analytics,
}: {
  analytics: any;
}) {
  if (!analytics) return null;
  const c = analytics.coverage;
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Rentabilidad y cobertura de datos</h3>
        <span className="badge">{analytics.methodology_version}</span>
      </div>
      <div className="metrics-grid">
        {Object.entries(analytics.metrics).map(([key, m]: [string, any]) => (
          <article className="metric" key={key}>
            <span>{m.label}</span>
            <strong>{pct(m.value)}</strong>
            <small>
              {m.value == null
                ? m.reason
                : "Base anual · cierre " + m.period_end}
            </small>
            <details>
              <summary>Fórmula y fuentes</summary>
              <p className="formula">{m.formula}</p>
              {m.limitations.map((v: string) => (
                <p key={v}>{v}</p>
              ))}
              <pre>{JSON.stringify(m.inputs, null, 2)}</pre>
            </details>
          </article>
        ))}
      </div>
      <p className="muted">
        ROE y ROA usan la media de dos cierres; el ROIC es una aproximación
        contable, sin normalizar efectivo excedentario, arrendamientos ni
        partidas extraordinarias. Un ROE alto puede reflejar recompras o
        apalancamiento.
      </p>
      {c.annual_data_outdated && (
        <p className="notice">
          El último ejercicio tiene más de 550 días; las cifras son históricas y
          los múltiplos anuales no se calculan.
        </p>
      )}
      <h3>
        Cobertura: {c.present_count} de {c.expected_count} campos
      </h3>
      <p>{c.interpretation}</p>
      <div className="ratio-grid">
        <div>
          <span>Ejercicios anuales</span>
          <b>{c.annual_periods}</b>
        </div>
        <div>
          <span>Trimestres disponibles</span>
          <b>{c.quarters}</b>
        </div>
        <div>
          <span>TTM</span>
          <b>{c.ttm_available ? "Disponible" : "Sin cobertura suficiente"}</b>
        </div>
        <div>
          <span>Precio: antigüedad</span>
          <b>{num(c.quote_age_days, 1)} días</b>
        </div>
        <div>
          <span>Divisa de precio compatible</span>
          <b>{c.quote_currency_compatible ? "Sí" : "No"}</b>
        </div>
        <div>
          <span>Balance independiente</span>
          <b>
            {c.balance_check.status === "consistent"
              ? "Cuadra"
              : c.balance_check.status === "requires_review"
                ? "Revisar diferencias"
                : "No comprobable"}
          </b>
        </div>
      </div>
      <details>
        <summary>Datos ausentes y controles</summary>
        <p>
          Ausentes:{" "}
          {c.missing_fields.join(", ") || "Ninguno de los campos seleccionados"}
        </p>
        <p>
          Divisas inconsistentes:{" "}
          {c.currency_mismatches.join(", ") || "Ninguna detectada"}
        </p>
        <p>
          Fechas por revisar:{" "}
          {c.chronology_issues.join(", ") || "Ninguna detectada"}
        </p>
        <p>
          Campos sin procedencia completa:{" "}
          {c.fields_without_provenance.join(", ") || "Ninguno detectado"}
        </p>
        <pre>
          {JSON.stringify(
            { balance: c.balance_check, excluded_fields: c.excluded_fields },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
