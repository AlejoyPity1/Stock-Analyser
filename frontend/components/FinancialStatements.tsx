"use client";
import { useState } from "react";
import { compact, num } from "./api";
const labels: Record<string, string> = {
  revenue: "Ingresos",
  cost_revenue: "Coste de ventas",
  gross_profit: "Beneficio bruto",
  ebit: "EBIT",
  net_income: "Beneficio neto",
  eps: "EPS diluido reportado",
  shares: "Acciones diluidas medias",
  cash: "Efectivo",
  assets: "Activos",
  current_assets: "Activo corriente",
  debt: "Deuda financiera",
  liabilities: "Pasivos",
  current_liabilities: "Pasivo corriente",
  equity: "Patrimonio",
  ocf: "Flujo operativo",
  capex: "Capex",
  da: "D&A",
  sbc: "Remuneración en acciones",
  dividends: "Dividendos pagados",
  buybacks: "Recompras",
  interest: "Gastos financieros",
};
export default function FinancialStatements({ company }: { company: any }) {
  const [period, setPeriod] = useState("annual");
  const rows =
    period === "annual"
      ? company.statements
      : period === "quarterly"
        ? company.quarterly || []
        : company.ttm
          ? [company.ttm]
          : [];
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Estados financieros · {company.currency}</h3>
        <label>
          Base del estado
          <select
            aria-label="Base del estado"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="annual">Anual</option>
            <option value="quarterly">Trimestral</option>
            <option value="ttm">TTM</option>
          </select>
        </label>
      </div>
      <p className="muted">
        Importes absolutos. TTM requiere cuatro trimestres independientes,
        contiguos y de la misma divisa. Las acciones se ponderan por días; no se
        suman.
      </p>
      {rows.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Partida</th>
                {rows.map((r: any) => (
                  <th key={r.end}>{r.end}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(labels).map(([key, label]) => (
                <tr key={key}>
                  <td>{label}</td>
                  {rows.map((row: any) => {
                    const fact = row.values[key];
                    return (
                      <td key={row.end}>
                        {fact ? (
                          <details className="fact">
                            <summary>
                              {key === "eps"
                                ? num(fact.value)
                                : compact(fact.value)}
                              {fact.quality === "derived" ? " *" : ""}
                            </summary>
                            <div>
                              <b>
                                {num(fact.value, 4)} {fact.unit}
                              </b>
                              <p>{fact.tag}</p>
                              <p>
                                Período: {fact.period_start || "Saldo a"} →{" "}
                                {fact.period_end}
                              </p>
                              <p>Publicado: {fact.filed}</p>
                              <p>{fact.formula}</p>
                              <a
                                href={fact.source}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Fuente SEC ↗
                              </a>
                              {fact.components && (
                                <>
                                  <p>Componentes de cálculo:</p>
                                  {fact.components.map((c: any, i: number) => (
                                    <p key={i}>
                                      {num(c.value, 4)} {c.unit} ·{" "}
                                      {c.period_start || "Saldo"} →{" "}
                                      {c.period_end} · {c.source_id}
                                    </p>
                                  ))}
                                </>
                              )}
                            </div>
                          </details>
                        ) : (
                          "—"
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">
          <h3>Sin períodos compatibles</h3>
          <p>
            SEC no proporciona los trimestres necesarios para construir esta
            base. No se reparte un dato anual entre cuatro para inventar
            trimestres.
          </p>
        </div>
      )}
      <p className="footnote">
        * Cálculo derivado con componentes trazables. Los flujos acumulados se
        restan para obtener trimestres; el EPS diluido no se deriva por resta.
        Pulsa las cifras para inspeccionar fuentes y fórmulas.
      </p>
    </section>
  );
}
