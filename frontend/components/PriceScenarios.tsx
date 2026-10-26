"use client";
import { useEffect, useState } from "react";
import { api, num, pct, date, download } from "./api";
import HorizonSummary from "./HorizonSummary";

const names: Record<string, string> = {
  bear: "Bajista",
  base: "Base",
  bull: "Alcista",
};
const blank = () =>
  Object.fromEntries(
    ["3", "6"].map((months) => [
      months,
      Object.fromEntries(
        Object.keys(names).map((name) => [
          name,
          {
            forward_eps: "",
            pe: "",
            dividends_per_share: "",
            rationale: "",
            invalidation: "",
          },
        ]),
      ),
    ]),
  );

export default function PriceScenarios({
  symbol,
  quote,
  research,
}: {
  symbol?: string;
  quote?: any;
  research?: any;
}) {
  const [target, setTarget] = useState(symbol || ""),
    [currency, setCurrency] = useState(quote?.currency || ""),
    [horizon, setHorizon] = useState("3-6m"),
    [forms, setForms] = useState<any>(blank),
    [month, setMonth] = useState("3"),
    [caseName, setCaseName] = useState("base"),
    [events, setEvents] = useState<any[]>([]),
    [selected, setSelected] = useState<string[]>([]),
    [history, setHistory] = useState<any[]>([]),
    [result, setResult] = useState<any>(null),
    [revision, setRevision] = useState(0),
    [calculated, setCalculated] = useState(-1),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    setTarget(symbol || "");
    setCurrency(quote?.currency || "");
    setForms(blank());
    setResult(null);
    setSelected([]);
  }, [symbol, quote?.currency]);
  useEffect(() => {
    if (research && research.symbol === symbol) {
      const h = research.investment_horizon?.code || "3-6m";
      setHorizon(h);
      setMonth(h === "6m" ? "6" : "3");
    }
  }, [research?.id, symbol]);
  useEffect(() => {
    let active = true;
    setHistory([]);
    setEvents([]);
    if (!/^[A-Z][A-Z0-9.\-]{0,14}$/.test(target.trim())) return;
    const timer = setTimeout(
      () =>
        Promise.all([
          api("/records?kind=price_scenario&symbol=" + target.trim()),
          api("/catalysts?symbol=" + target.trim()),
        ])
          .then(([saved, catalysts]) => {
            if (active) {
              setHistory(saved);
              setEvents(catalysts.items);
            }
          })
          .catch((e) => {
            if (active) setError(e.message);
          }),
      350,
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [target]);
  const months = horizon === "3-6m" ? ["3", "6"] : [horizon[0]];
  function dirty() {
    setRevision((old) => old + 1);
  }
  function payload() {
    const body: any = {
      symbol: target.trim(),
      currency: currency.trim(),
      horizon,
      catalyst_ids: selected,
      research_id: research?.symbol === target.trim() ? research.id : null,
    };
    for (const m of months)
      body[m === "3" ? "three_months" : "six_months"] = Object.fromEntries(
        Object.keys(names).map((key) => {
          const form = forms[m][key];
          const values: any = {
            rationale: form.rationale,
            invalidation: form.invalidation,
          };
          for (const field of ["forward_eps", "pe", "dividends_per_share"]) {
            if (
              String(form[field]).trim() === "" ||
              !Number.isFinite(Number(form[field]))
            )
              throw new Error(
                `Completa ${field} del caso ${names[key]} a ${m} meses; cero dividendos también debe indicarse.`,
              );
            values[field] = Number(form[field]);
          }
          return [key, values];
        }),
      );
    return body;
  }
  async function calculate(save = false) {
    setBusy(true);
    setError("");
    const current = revision;
    try {
      const body = payload();
      const value = await api(
        save ? "/price-scenarios" : "/price-scenarios/preview",
        body,
      );
      setResult(value);
      setCalculated(current);
      if (save)
        setHistory(
          await api("/records?kind=price_scenario&symbol=" + body.symbol),
        );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  function restore(value: any) {
    setTarget(value.symbol);
    setCurrency(value.currency);
    setHorizon(value.inputs.horizon);
    setMonth(value.inputs.horizon === "6m" ? "6" : "3");
    const next = blank();
    for (const [m, key] of [
      ["3", "three_months"],
      ["6", "six_months"],
    ])
      if (value.inputs[key])
        next[m] = Object.fromEntries(
          Object.entries(value.inputs[key]).map(
            ([name, form]: [string, any]) => [
              name,
              {
                forward_eps: String(form.forward_eps),
                pe: String(form.pe),
                dividends_per_share: String(form.dividends_per_share),
                rationale: String(form.rationale),
                invalidation: String(form.invalidation),
              },
            ],
          ),
        );
    setForms(next);
    setSelected(value.inputs.catalyst_ids);
    setResult(value);
    setRevision(0);
    setCalculated(0);
  }
  const form = forms[month][caseName];
  return (
    <section className="panel">
      <h3>Escenarios de cotización · 3 y 6 meses</h3>
      <p className="muted">
        Precio condicional = EPS forward de 12 meses en la fecha objetivo × P/E
        supuesto. Introduce tus hipótesis para la misma acción/ADR y divisa del
        precio. No son previsiones del sistema. Cada horizonte se calcula por
        separado; no se prorratea el beneficio anual.
      </p>
      <div className="form-grid">
        <label>
          Empresa de escenarios
          <input
            aria-label="Empresa de escenarios"
            value={target}
            placeholder="Ticker"
            onChange={(e) => {
              setTarget(e.target.value.toUpperCase());
              setCurrency("");
              setForms(blank());
              setSelected([]);
              setResult(null);
              dirty();
            }}
          />
        </label>
        <label>
          Divisa de EPS y precio
          <input
            aria-label="Divisa de escenarios de cotización"
            value={currency}
            maxLength={3}
            onChange={(e) => {
              setCurrency(e.target.value.toUpperCase());
              dirty();
            }}
            placeholder="USD"
          />
        </label>
        <label>
          Horizonte
          <select
            aria-label="Horizonte de escenarios de cotización"
            value={horizon}
            onChange={(e) => {
              setHorizon(e.target.value);
              setMonth(e.target.value === "6m" ? "6" : "3");
              dirty();
            }}
          >
            <option value="3-6m">3 y 6 meses</option>
            <option value="3m">3 meses</option>
            <option value="6m">6 meses</option>
          </select>
        </label>
      </div>
      <div className="tabs">
        {months.map((m) => (
          <button
            key={m}
            className={month === m ? "selected" : ""}
            onClick={() => setMonth(m)}
          >
            Casos a {m} meses
          </button>
        ))}
      </div>
      <div className="tabs">
        {Object.entries(names).map(([key, name]) => (
          <button
            key={key}
            className={caseName === key ? "selected" : ""}
            onClick={() => setCaseName(key)}
          >
            {name}
          </button>
        ))}
      </div>
      <h4>
        {names[caseName]} · {month} meses
      </h4>
      <div className="form-grid">
        {[
          ["forward_eps", "EPS forward 12 meses"],
          ["pe", "P/E supuesto"],
          ["dividends_per_share", "Dividendos por acción del horizonte"],
        ].map(([key, label]) => (
          <label key={key}>
            {label}
            <input
              type="number"
              step="any"
              aria-label={label}
              value={form[key]}
              onChange={(e) => {
                setForms((old: any) => ({
                  ...old,
                  [month]: {
                    ...old[month],
                    [caseName]: {
                      ...old[month][caseName],
                      [key]: e.target.value,
                    },
                  },
                }));
                dirty();
              }}
            />
          </label>
        ))}
      </div>
      <label>
        Fundamento del escenario
        <textarea
          aria-label="Fundamento del escenario de cotización"
          value={form.rationale}
          onChange={(e) => {
            setForms((old: any) => ({
              ...old,
              [month]: {
                ...old[month],
                [caseName]: {
                  ...old[month][caseName],
                  rationale: e.target.value,
                },
              },
            }));
            dirty();
          }}
          placeholder="Justifica EPS, múltiplo y dividendos (mínimo 30 caracteres)."
        />
      </label>
      <label>
        Condición de invalidación
        <textarea
          aria-label="Invalidación del escenario de cotización"
          value={form.invalidation}
          onChange={(e) => {
            setForms((old: any) => ({
              ...old,
              [month]: {
                ...old[month],
                [caseName]: {
                  ...old[month][caseName],
                  invalidation: e.target.value,
                },
              },
            }));
            dirty();
          }}
          placeholder="Qué dato observable invalidaría este caso (mínimo 20 caracteres)."
        />
      </label>
      <details>
        <summary>Catalizadores vinculados ({selected.length})</summary>
        {events.map((event) => (
          <label className="toggle" key={event.id}>
            <input
              type="checkbox"
              checked={selected.includes(event.id)}
              onChange={(e) => {
                setSelected((old) =>
                  e.target.checked
                    ? [...old, event.id]
                    : old.filter((id) => id !== event.id),
                );
                dirty();
              }}
            />
            {event.title} · {event.event_date || "Sin fecha"} ·{" "}
            {event.date_status}
          </label>
        ))}
        <p className="muted">
          Se conservan las versiones elegidas; su efecto debe estar reflejado
          una sola vez en tus supuestos. No hay suma automática del impacto de
          noticias.
        </p>
      </details>
      <p className="muted">
        Los dividendos son hipótesis explícitas, incluso cuando sean cero.
        Calcular y guardar recuperan la cotización disponible; cada resultado
        conserva su referencia. Sin probabilidades automáticas.
      </p>
      <div className="buttons">
        <button className="primary" disabled={busy} onClick={() => calculate()}>
          Calcular escenarios de cotización
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => calculate(true)}
        >
          Guardar escenarios de cotización
        </button>
      </div>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      {result && (
        <div>
          {revision !== calculated && (
            <p className="notice">
              Hay cambios sin recalcular. Se muestra el resultado de los inputs
              conservados abajo.
            </p>
          )}
          <HorizonSummary horizon={result.investment_horizon} />
          <p>
            Precio inicial: {num(result.reference_quote.price)}{" "}
            {result.currency} · {date(result.reference_quote.timestamp)}
          </p>
          {Object.entries(result.horizons).map(
            ([months, value]: [string, any]) => (
              <div key={months}>
                <h4>
                  Resultados a {months} meses · {value.target_date}
                </h4>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Caso</th>
                        <th>Precio condicional</th>
                        <th>Retorno de precio</th>
                        <th>Retorno con dividendos</th>
                        <th>P/E de equilibrio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(value.cases).map(
                        ([key, c]: [string, any]) => (
                          <tr key={key}>
                            <td>{names[key]}</td>
                            <td>
                              {num(c.price)} {result.currency}
                            </td>
                            <td>{pct(c.price_return)}</td>
                            <td>{pct(c.gross_return_with_dividends)}</td>
                            <td>{num(c.breakeven_pe)}×</td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
                <p>
                  Relación condicional beneficio/riesgo:{" "}
                  {num(value.conditional_reward_risk)} ·{" "}
                  {value.reward_risk_interpretation}
                </p>
              </div>
            ),
          )}
          <details>
            <summary>Inputs y evidencia conservados</summary>
            <pre>
              {JSON.stringify(
                { inputs: result.inputs, catalysts: result.catalysts },
                null,
                2,
              )}
            </pre>
          </details>
          {result.limitations.map((text: string) => (
            <p className="muted" key={text}>
              {text}
            </p>
          ))}
          <button
            className="secondary"
            onClick={() =>
              download("escenarios-" + result.symbol + ".json", result)
            }
          >
            Exportar escenarios JSON
          </button>
          {result.id && (
            <p role="status">
              Escenarios de cotización guardados · {result.id}
            </p>
          )}
        </div>
      )}
      {history.length > 0 && (
        <div>
          <h4>Historial de escenarios de cotización</h4>
          {history.map((row) => (
            <button
              className="saved-row"
              key={row.id}
              onClick={() => restore(row.data)}
            >
              <span>{date(row.created_at)}</span>
              <b>
                {row.symbol} · {row.data.investment_horizon.label}
              </b>
              <span>Abrir versión conservada</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
