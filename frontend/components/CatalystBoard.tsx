"use client";
import { useEffect, useState } from "react";
import { api, date } from "./api";

const empty = {
  title: "",
  category: "other",
  eventDate: "",
  dateStatus: "unknown",
  status: "planned",
  hypothesis: "",
  invalidation: "",
  sourceUrl: "",
  quote: "",
  sourceId: "",
  researchId: "",
  previousId: "",
};
const positions: Record<string, string> = {
  past: "Fecha pasada",
  within_horizon: "Dentro de 6 meses",
  beyond_horizon: "Fuera de 6 meses",
  undated: "Sin fecha",
  cancelled: "Cancelado",
};

export default function CatalystBoard({
  symbol,
  research,
}: {
  symbol?: string;
  research?: any;
}) {
  const [target, setTarget] = useState(symbol || ""),
    [form, setForm] = useState(empty),
    [items, setItems] = useState<any[]>([]),
    [calendar, setCalendar] = useState<any>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [saved, setSaved] = useState(""),
    [editorOpen, setEditorOpen] = useState(false);
  useEffect(() => {
    setTarget(symbol || "");
    setForm(empty);
    setCalendar(null);
  }, [symbol]);
  useEffect(() => {
    let active = true;
    setItems([]);
    setCalendar(null);
    setSaved("");
    if (!/^[A-Z][A-Z0-9.\-]{0,14}$/.test(target.trim())) return;
    const timer = setTimeout(
      () =>
        api("/catalysts?symbol=" + encodeURIComponent(target.trim()))
          .then((r) => {
            if (active) setItems(r.items);
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
  const sources =
    research?.symbol === target.trim()
      ? research.sources?.filter((s: any) =>
          ["read", "abstract_only"].includes(s.read_status),
        ) || []
      : [];
  function field(key: keyof typeof empty, value: string) {
    setForm((old) => ({ ...old, [key]: value }));
    setSaved("");
  }
  async function save() {
    setBusy(true);
    setError("");
    setSaved("");
    try {
      const result = await api("/catalysts", {
        symbol: target.trim(),
        title: form.title,
        category: form.category,
        event_date: form.eventDate || null,
        date_status: form.dateStatus,
        status: form.status,
        hypothesis: form.hypothesis,
        invalidation: form.invalidation,
        source_url: form.sourceUrl || null,
        evidence_quote: form.quote,
        source_id: form.sourceId || null,
        research_id: form.sourceId
          ? form.researchId
          : research?.symbol === target.trim()
            ? research.id
            : null,
        previous_id: form.previousId || null,
      });
      setItems(
        (await api("/catalysts?symbol=" + encodeURIComponent(target.trim())))
          .items,
      );
      setForm(empty);
      setEditorOpen(false);
      setSaved(result.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  async function loadCalendar() {
    setBusy(true);
    setError("");
    setCalendar(null);
    try {
      setCalendar(
        await api(
          "/companies/" +
            encodeURIComponent(target.trim()) +
            "/earnings-calendar",
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h3>Registro de catalizadores</h3>
      <p className="muted">
        Fechas, hipótesis y condiciones de invalidación revisadas por ti. El
        calendario de resultados del proveedor es orientativo y puede estar
        incompleto. No se infieren fechas futuras de la publicación de una
        noticia.
      </p>
      <div className="form-grid">
        <label>
          Empresa del catalizador
          <input
            aria-label="Empresa del catalizador"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value.toUpperCase());
              setForm(empty);
            }}
            placeholder="Ticker"
          />
        </label>
        <div className="buttons">
          <button
            className="secondary"
            disabled={busy || !target.trim()}
            onClick={loadCalendar}
          >
            Consultar calendario de resultados
          </button>
        </div>
      </div>
      {calendar && (
        <div>
          <p>{calendar.coverage}</p>
          {!calendar.items.length && (
            <p>
              No hay fechas devueltas para esta ventana; no equivale a ausencia
              de eventos.
            </p>
          )}
          {calendar.items.map((item: any, i: number) => (
            <div className="saved-row" key={i}>
              <span>
                {item.event_date} · {item.title} · fecha estimada
              </span>
              <button
                className="text-button"
                onClick={() => {
                  setForm({
                    ...empty,
                    title: item.title,
                    category: "earnings",
                    eventDate: item.event_date,
                    dateStatus: "estimated",
                    sourceUrl: item.source_url,
                  });
                  setEditorOpen(true);
                  setSaved("");
                }}
              >
                Usar como estimación
              </button>
            </div>
          ))}
        </div>
      )}
      <details
        open={editorOpen}
        onToggle={(e) => setEditorOpen(e.currentTarget.open)}
      >
        <summary>
          {form.previousId
            ? "Editar catalizador · se guardará una nueva versión"
            : "Registrar catalizador y evidencia"}
        </summary>
        <div className="form-grid">
          <label>
            Título
            <input
              aria-label="Título del catalizador"
              value={form.title}
              onChange={(e) => field("title", e.target.value)}
            />
          </label>
          <label>
            Categoría
            <select
              value={form.category}
              onChange={(e) => field("category", e.target.value)}
            >
              {[
                ["earnings", "Resultados"],
                ["guidance", "Guidance"],
                ["product", "Producto"],
                ["regulatory", "Regulación"],
                ["macro", "Macro"],
                ["other", "Otro"],
              ].map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Fecha del evento
            <input
              type="date"
              aria-label="Fecha del evento"
              value={form.eventDate}
              onChange={(e) =>
                setForm((old) => ({
                  ...old,
                  eventDate: e.target.value,
                  dateStatus: e.target.value
                    ? old.dateStatus === "unknown"
                      ? "estimated"
                      : old.dateStatus
                    : "unknown",
                }))
              }
            />
          </label>
          <label>
            Base de la fecha
            <select
              aria-label="Base de la fecha"
              value={form.dateStatus}
              onChange={(e) => {
                field("dateStatus", e.target.value);
                if (e.target.value === "unknown") field("eventDate", "");
              }}
            >
              <option value="unknown">Desconocida</option>
              <option value="estimated">Estimada</option>
              <option value="reported">
                Reportada en fuente · revisión manual
              </option>
            </select>
          </label>
          <label>
            Estado del evento
            <select
              aria-label="Estado del evento"
              value={form.status}
              onChange={(e) => field("status", e.target.value)}
            >
              <option value="planned">Previsto</option>
              <option value="occurred">Ocurrido</option>
              <option value="cancelled">Cancelado</option>
            </select>
          </label>
          <label>
            Referencia del expediente
            <select
              aria-label="Referencia del expediente"
              value={form.sourceId}
              onChange={(e) => {
                const source = sources.find(
                  (s: any) => s.id === e.target.value,
                );
                setForm((old) => ({
                  ...old,
                  sourceId: source?.id || "",
                  researchId: source ? research.id : "",
                  sourceUrl: source?.url || old.sourceUrl,
                }));
              }}
            >
              <option value="">Referencia externa manual</option>
              {form.sourceId &&
                !sources.some((s: any) => s.id === form.sourceId) && (
                  <option value={form.sourceId}>
                    Fuente original de esta versión
                  </option>
                )}
              {sources.map((source: any) => (
                <option key={source.id} value={source.id}>
                  {source.title}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Enlace de la fuente
          <input
            aria-label="Enlace de la fuente"
            type="url"
            value={form.sourceUrl}
            onChange={(e) => field("sourceUrl", e.target.value)}
            placeholder="https://…"
          />
        </label>
        <label>
          Cita de evidencia
          <textarea
            aria-label="Cita de evidencia"
            value={form.quote}
            onChange={(e) => field("quote", e.target.value)}
          />
        </label>
        <label>
          Hipótesis de impacto
          <textarea
            aria-label="Hipótesis de impacto"
            value={form.hypothesis}
            onChange={(e) => field("hypothesis", e.target.value)}
            placeholder="Qué podría cambiar y por qué (mínimo 30 caracteres)."
          />
        </label>
        <label>
          Condición que invalidaría la hipótesis
          <textarea
            aria-label="Invalidación del catalizador"
            value={form.invalidation}
            onChange={(e) => field("invalidation", e.target.value)}
            placeholder="Dato o evento observable que la invalidaría (mínimo 20 caracteres)."
          />
        </label>
        <p className="muted">
          Una referencia externa se guarda sin afirmar que su texto se haya
          verificado. Si eliges una fuente ya leída del expediente, se comprueba
          que la cita sea literal; la interpretación sigue siendo manual.
        </p>
        <div className="buttons">
          <button className="primary" disabled={busy} onClick={save}>
            {form.previousId
              ? "Guardar nueva versión del catalizador"
              : "Guardar catalizador"}
          </button>
          {form.previousId && (
            <button className="secondary" onClick={() => setForm(empty)}>
              Cancelar edición
            </button>
          )}
        </div>
      </details>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      {saved && <p role="status">Catalizador guardado · {saved}</p>}
      <div className="source-list">
        {items.map((item) => (
          <article className="source-card" key={item.id}>
            <h4>{item.title}</h4>
            <p>
              {item.event_date || "Sin fecha"} · {item.date_status} ·{" "}
              {item.status} · {positions[item.position]}
            </p>
            <p>{item.hypothesis}</p>
            <p>Se invalida si: {item.invalidation}</p>
            <small>
              {item.verification === "literal_quote_matched"
                ? "Cita literal coincidente; interpretación manual"
                : "Referencia externa sin verificación del texto"}{" "}
              · {date(item.created_at)}
            </small>
            <details>
              <summary>Fuente y versión conservadas</summary>
              <a href={item.source_url} target="_blank" rel="noreferrer">
                Referencia
              </a>
              <blockquote>
                {item.evidence_quote || "Sin cita literal"}
              </blockquote>
              <p>
                Evento {item.event_id} · versión {item.id}
              </p>
            </details>
            <button
              className="text-button"
              onClick={() => {
                setEditorOpen(true);
                setForm({
                  title: item.title,
                  category: item.category,
                  eventDate: item.event_date || "",
                  dateStatus: item.date_status,
                  status: item.status,
                  hypothesis: item.hypothesis,
                  invalidation: item.invalidation,
                  sourceUrl: item.source_url,
                  quote: item.evidence_quote,
                  sourceId: item.source_id || "",
                  researchId: item.research_id || "",
                  previousId: item.id,
                });
              }}
            >
              Editar en una nueva versión
            </button>
          </article>
        ))}
      </div>
      {!items.length && (
        <p className="muted">
          No hay catalizadores guardados para esta empresa.
        </p>
      )}
    </section>
  );
}
