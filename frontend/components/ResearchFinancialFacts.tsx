type Fact = { value: number; unit: string; source: string; filed?: string; quality?: string };
type Period = { period_type: string; period_start: string; period_end: string; values: Record<string, Fact> };

const metrics = [
  ["revenue", "Revenue"],
  ["net_income", "Net income"],
  ["eps", "Diluted EPS"],
  ["shares", "Weighted-average diluted shares"],
];

export default function ResearchFinancialFacts({ periods = [], withheld = 0 }: { periods?: Period[]; withheld?: number }) {
  if (!periods.length && !withheld) return null;
  return (
    <section aria-label="Reported financial context">
      <h3>Reported financial context</h3>
      <p className="muted">Figures come directly from the saved SEC financial data, with their original periods and units. They are historical context for the analysis.</p>
      {withheld > 0 && <p className="notice">{withheld} numerical financial statement(s) from the AI were withheld. Use the reported figures where available and review the remaining interpretations.</p>}
      {periods.map((period) => (
        <details key={period.period_type + period.period_end} open={period.period_type === "quarter"}>
          <summary>{period.period_type === "quarter" ? "Quarter" : period.period_type === "ttm" ? "TTM" : "Annual"}: {period.period_start} to {period.period_end}</summary>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Metric</th><th>Unscaled value</th><th>Unit</th><th>Source</th></tr></thead>
              <tbody>{metrics.map(([key, label]) => {
                const fact = period.values[key];
                return <tr key={key}>
                  <td>{label}</td>
                  <td>{fact ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 }).format(fact.value) : "Unavailable"}</td>
                  <td>{fact?.unit || "—"}</td>
                  <td>{fact && <a href={fact.source} target="_blank" rel="noreferrer">SEC · {fact.filed || "filing date unavailable"}{fact.quality === "derived" ? " · derived" : ""}</a>}</td>
                </tr>;
              })}</tbody>
            </table>
          </div>
        </details>
      ))}
      <p className="footnote">Share counts are weighted averages for the stated period, rather than current shares outstanding. Monetary values are unscaled; EPS is an amount per share.</p>
    </section>
  );
}
