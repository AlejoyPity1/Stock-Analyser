"use client";
import { useState } from "react";
import { num, pct } from "./api";
export default function MetricPanel({ data }: { data: any }) {
  const [basis, setBasis] = useState("annual");
  const metrics = basis === "annual" ? data.metrics : data.ttm_metrics;
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Ratios y bases de cálculo</h3>
        <label>
          Período de ratios
          <select value={basis} onChange={(e) => setBasis(e.target.value)}>
            <option value="annual">Último ejercicio anual</option>
            <option value="ttm">TTM</option>
          </select>
        </label>
      </div>
      {metrics ? (
        <>
          <p className="muted">
            Base:{" "}
            {basis === "annual"
              ? data.company.statements[0]?.end
              : data.company.ttm?.end}{" "}
            · {data.company.currency}. Precio más reciente disponible, cuando su
            divisa coincide. Acciones diluidas medias del período; no acciones
            puntuales actuales.
          </p>
          <div className="ratio-grid">
            {Object.entries(metrics).map(([k, v]) => (
              <div key={k}>
                <span>{k.replaceAll("_", " ")}</span>
                <b>
                  {k.includes("margin") || k.includes("yield")
                    ? pct(v)
                    : num(v)}
                </b>
              </div>
            ))}
          </div>
          <p className="muted">
            P/E = capitalización / beneficio atribuible a propietarios; EV =
            capitalización + deuda neta. FCF = OCF − capex. Los ratios ROE/ROA
            de esta tabla usan saldo final; los de patrimonio y activos medios
            se muestran por separado. EBITDA = EBIT + D&A si ambos existen.
          </p>
        </>
      ) : (
        <p className="muted">
          No hay cuatro trimestres compatibles para calcular ratios TTM. No se
          sustituye por el ejercicio anual.
        </p>
      )}
    </section>
  );
}
