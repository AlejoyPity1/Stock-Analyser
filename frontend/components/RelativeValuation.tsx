"use client";
import { useEffect, useState } from "react";
import { api, num, pct, date, download } from "./api";
export default function RelativeValuation({
  symbol,
  researchId,
}: {
  symbol?: string;
  researchId?: string;
}) {
  const [target, setTarget] = useState(symbol || ""),
    [peers, setPeers] = useState(""),
    [metric, setMetric] = useState("pe"),
    [basis, setBasis] = useState("annual"),
    [rationale, setRationale] = useState(""),
    [result, setResult] = useState<any>(null),
    [saved, setSaved] = useState<any[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    setTarget(symbol || "");
    setResult(null);
  }, [symbol]);
  useEffect(() => {
    if (!target.trim()) {
      setSaved([]);
      return;
    }
    let active = true;
    api("/records?kind=relative&symbol=" + encodeURIComponent(target.trim()))
      .then((r) => {
        if (active) setSaved(r);
      })
      .catch(() => {
        if (active) setSaved([]);
      });
    return () => {
      active = false;
    };
  }, [target]);
  async function calculate(save = false) {
    setBusy(true);
    setError("");
    try {
      const body = {
        target: target.trim().toUpperCase(),
        peers: peers
          .split(",")
          .map((v) => v.trim().toUpperCase())
          .filter(Boolean),
        metric,
        basis,
        rationale,
        research_id: target.trim() === symbol ? researchId || null : null,
      };
      const data = await api(
        save ? "/relative-valuations" : "/relative-analysis",
        body,
      );
      setResult(data);
      if (save) setSaved(await api("/records?kind=relative&symbol=" + body.target));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  const changed =
    !!result &&
    (target.trim() !== result.inputs.target ||
      peers
        .split(",")
        .map((v) => v.trim().toUpperCase())
        .filter(Boolean)
        .join(",") !== result.inputs.peers.join(",") ||
      metric !== result.inputs.metric ||
      basis !== result.inputs.basis ||
      rationale !== result.inputs.rationale);
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Valoración por comparables</h3>
        <span className="badge">
          DATOS REALES · HIPÓTESIS DE COMPARABILIDAD
        </span>
      </div>
      <p className="muted">
        Selecciona al menos dos pares y justifica el grupo: negocio,
        crecimiento, márgenes y riesgos. Un mismo sector no certifica
        comparabilidad. Se exigen monedas de reporte compatibles, cierres a ≤92
        días y precios de ≤7 días. No se utilizan estimaciones forward.
      </p>
      <div className="form-grid">
        <label>
          Empresa objetivo
          <input
            aria-label="Empresa objetivo de comparables"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value.toUpperCase());
              setResult(null);
            }}
            placeholder="Ticker"
          />
        </label>
        <label>
          Pares, separados por coma
          <input
            aria-label="Pares de valoración"
            value={peers}
            onChange={(e) => setPeers(e.target.value)}
            placeholder="Tickers elegidos por ti"
          />
        </label>
        <label>
          Múltiplo
          <select
            aria-label="Múltiplo de valoración relativa"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            <option value="pe">P/E</option>
            <option value="ev_ebitda">EV / EBITDA</option>
            <option value="ev_revenue">EV / Revenue</option>
            <option value="p_fcf">P / FCF</option>
          </select>
        </label>
        <label>
          Base financiera
          <select
            aria-label="Base de valoración relativa"
            value={basis}
            onChange={(e) => setBasis(e.target.value)}
          >
            <option value="annual">Anual</option>
            <option value="ttm">TTM</option>
          </select>
        </label>
      </div>
      <label>
        Justificación de comparabilidad
        <textarea
          aria-label="Justificación de comparabilidad"
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          placeholder="Explica similitudes y diferencias relevantes del grupo (mínimo 30 caracteres)."
        />
      </label>
      <div className="buttons">
        <button
          className="primary"
          disabled={busy || rationale.trim().length < 30}
          onClick={() => calculate()}
        >
          Calcular comparables
        </button>
        <button
          className="secondary"
          disabled={busy || rationale.trim().length < 30}
          onClick={() => calculate(true)}
        >
          Guardar valoración relativa
        </button>
      </div>
      {busy && (
        <p role="status">Recuperando y validando datos de los comparables…</p>
      )}
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      {result && (
        <div className="relative-result">
          {changed && (
            <p className="notice">
              Hay cambios sin recalcular. El resultado conserva los inputs de la
              última ejecución, visibles abajo.
            </p>
          )}
          <h3>
            {result.status === "available"
              ? "Valor implícito condicional"
              : "No hay una base suficiente para valorar"}
          </h3>
          <p>
            Pares válidos: {result.accepted_count} de {result.selected_count}.
            Base: {result.inputs.basis}. Justificación:{" "}
            {result.inputs.rationale}
          </p>
          {result.target.reasons?.map((v: string) => (
            <p className="error-text" key={v}>
              Objetivo: {v}
            </p>
          ))}
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Par</th>
                  <th>Divisa / período</th>
                  <th>Múltiplo</th>
                  <th>Margen EBIT</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {result.peers.map((p: any) => (
                  <tr key={p.symbol}>
                    <td>
                      {p.symbol}
                      <small>{p.name}</small>
                    </td>
                    <td>
                      {p.currency} / {p.period_end}
                    </td>
                    <td>{num(p.multiple)}×</td>
                    <td>{pct(p.operating_margin)}</td>
                    <td>
                      {p.eligible ? "Admitido" : "Excluido"}
                      <small>{p.reasons.join("; ")}</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.distribution && (
            <>
              <div className="metrics-grid">
                <div className="metric">
                  <span>Mediana del grupo</span>
                  <strong>{num(result.distribution.median)}×</strong>
                  <small>
                    Rango {num(result.distribution.min)}–
                    {num(result.distribution.max)}×
                  </small>
                </div>
                <div className="metric">
                  <span>Valor por múltiplos</span>
                  <strong>{num(result.implied_per_share)}</strong>
                  <small>
                    {result.currency} / acción · condicionado al grupo
                  </small>
                </div>
                <div className="metric">
                  <span>Upside condicional</span>
                  <strong>{pct(result.upside)}</strong>
                  <small>No es una previsión de cotización</small>
                </div>
                <div className="metric">
                  <span>Prima del múltiplo actual</span>
                  <strong>{pct(result.market_multiple_gap)}</strong>
                  <small>Múltiplo objetivo / mediana − 1</small>
                </div>
              </div>
              <p className="formula">{result.formula}</p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Múltiplo del grupo</th>
                      {result.sensitivity.map((s: any, i: number) => (
                        <th key={i}>{num(s.multiple)}×</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Valor / acción ({result.currency})</td>
                      {result.sensitivity.map((s: any, i: number) => (
                        <td key={i}>{num(s.implied_per_share)}</td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
              <details>
                <summary>Inputs y snapshots de cálculo</summary>
                <pre>
                  {JSON.stringify(
                    { target: result.target, peers: result.peers },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </>
          )}
          {result.limitations.map((v: string) => (
            <p className="footnote" key={v}>
              {v}
            </p>
          ))}
          <button
            className="secondary"
            onClick={() =>
              download("comparables-" + result.symbol + ".json", result)
            }
          >
            Exportar cálculo JSON
          </button>
          {result.id && <p>Versión guardada · {date(result.created_at)}</p>}
        </div>
      )}
      {saved.length > 0 && (
        <div>
          <h3>Valoraciones relativas guardadas</h3>
          {saved.map((r) => (
            <button
              className="saved-row"
              key={r.id}
              onClick={() => {
                setResult(r.data);
                setTarget(r.data.inputs.target);
                setPeers(r.data.inputs.peers.join(","));
                setMetric(r.data.inputs.metric);
                setBasis(r.data.inputs.basis);
                setRationale(r.data.inputs.rationale);
              }}
            >
              <span>{date(r.created_at)}</span>
              <b>
                {num(r.data.implied_per_share)} {r.data.currency}
              </b>
              <span>
                {r.data.inputs.metric} · {r.data.inputs.rationale}
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
