"use client";

import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  FileText,
  FolderOpen,
  Search,
  ShieldCheck,
  Star,
  Target,
} from "lucide-react";
import { date, num } from "./api";
import { horizonLabels, statusLabels } from "./workspace";

type Props = {
  query: string;
  onQuery: (value: string) => void;
  onSearch: (event: React.FormEvent) => void;
  onLoad: (symbol: string) => void;
  onNavigate: (section: string) => void;
  onReport: (id: string) => void;
  recent: any[];
  reports: any[];
  watch: any[];
  horizon: string;
  onHorizon: (value: string) => void;
  busy: boolean;
  loading: boolean;
  loadError: boolean;
  localAIEnabled: boolean;
  localAIModel: string;
  onRetry: () => void;
};

export default function WorkspaceHome(props: Props) {
  const [showAll, setShowAll] = useState(false);
  // Multiple saved snapshots must not appear as different companies.
  const companies = props.recent.filter(
    (r, i, rows) => rows.findIndex((other) => other.symbol === r.symbol) === i,
  );
  const reports = props.reports.slice(0, 3);
  const stats = [
    {
      label: "Empresas consultadas",
      value: companies.length,
      Icon: FolderOpen,
    },
    {
      label: "Investigaciones guardadas",
      value: props.reports.length,
      Icon: FileText,
    },
    { label: "En seguimiento", value: props.watch.length, Icon: Star },
  ];
  const unavailable = props.loading || props.loadError;
  return (
    <div className="workspace-home">
      <section className="discovery" aria-labelledby="discovery-title">
        <div className="discovery-copy">
          <span className="eyebrow">
            <span className="live-dot" /> TU PRÓXIMA INVESTIGACIÓN
          </span>
          <h2 id="discovery-title">
            Una acción.
            <br />
            <em>Todo el contexto.</em>
          </h2>
          <p>
            Entiende qué puede mover su precio. Conecta los datos, los próximos
            eventos y tus escenarios de inversión.
          </p>
          <form onSubmit={props.onSearch} className="discovery-search">
            <Search size={21} aria-hidden="true" />
            <input
              aria-label="Ticker para investigar"
              value={props.query}
              onChange={(e) => props.onQuery(e.target.value)}
              placeholder="¿Qué empresa quieres analizar?"
              autoComplete="off"
            />
            <button
              className="primary"
              disabled={props.busy || !props.query.trim()}
            >
              Buscar acción <ArrowRight size={17} />
            </button>
          </form>
          <div className="discovery-examples">
            <span>Prueba con</span>
            {["AAPL", "ASML", "GPRK"].map((symbol) => (
              <button
                disabled={props.busy}
                key={symbol}
                onClick={() => props.onLoad(symbol)}
              >
                {symbol}
                <ArrowUpRight size={12} />
              </button>
            ))}
            <span>o escribe otro ticker</span>
          </div>
          <small className="coverage-note">
            Disponibilidad según empresa, mercado y fuentes.
          </small>
        </div>
        <div className="horizon-card">
          <div className="horizon-card-label">
            <CalendarDays size={16} /> TU HORIZONTE
          </div>
          <strong>{horizonLabels[props.horizon]}</strong>
          <p>El plazo de tu próxima investigación.</p>
          <div
            className="horizon-switch"
            role="group"
            aria-label="Horizonte de la próxima investigación"
          >
            {Object.entries(horizonLabels).map(([code, label]) => (
              <button
                key={code}
                aria-pressed={props.horizon === code}
                onClick={() => props.onHorizon(code)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="horizon-roadmap">
            <div>
              <BookOpen size={17} />
              <span>
                Recopila evidencia<small>Noticias y documentos oficiales</small>
              </span>
            </div>
            <div>
              <CalendarDays size={17} />
              <span>
                Identifica catalizadores
                <small>Resultados, eventos y riesgos</small>
              </span>
            </div>
            <div>
              <Target size={17} />
              <span>
                Construye escenarios<small>Bajista, base y alcista</small>
              </span>
            </div>
          </div>
        </div>
      </section>

      <div className="workspace-stats" aria-label="Actividad de tu espacio">
        {stats.map(({ label, value, Icon }) => (
          <div key={label}>
            <span className="stat-icon">
              <Icon size={19} />
            </span>
            <div>
              <strong>{unavailable ? "—" : value}</strong>
              <span>{label}</span>
            </div>
          </div>
        ))}
        <div className="workspace-scope">
          <ShieldCheck size={19} />
          <span>
            Tus fuentes, a la vista
            <small>Hipótesis y cálculos revisables</small>
          </span>
        </div>
      </div>

      <div className="dashboard-columns">
        <section
          className="panel recent-companies"
          aria-labelledby="recent-companies-title"
        >
          <div className="panel-heading">
            <div>
              <span className="eyebrow">CONTINÚA DONDE LO DEJASTE</span>
              <h3 id="recent-companies-title">Empresas recientes</h3>
            </div>
            <span className="count-label">
              {unavailable ? "—" : companies.length}
            </span>
          </div>
          {props.loading ? (
            <div className="dashboard-empty" role="status">
              <FolderOpen size={24} />
              <h4>Cargando tu espacio…</h4>
              <p>Recuperando empresas y análisis guardados.</p>
            </div>
          ) : props.loadError ? (
            <div className="dashboard-empty">
              <FolderOpen size={24} />
              <h4>No pudimos cargar tu actividad</h4>
              <button className="secondary" onClick={props.onRetry}>
                Reintentar
              </button>
            </div>
          ) : companies.length ? (
            <>
              <div className="company-list-caption">
                <span>EMPRESA</span>
                <span>PRECIO GUARDADO</span>
              </div>
              {companies.slice(0, showAll ? undefined : 5).map((r) => (
                <button
                  className="company-row"
                  key={r.id}
                  disabled={props.busy}
                  onClick={() => props.onLoad(r.symbol)}
                >
                  <span className="ticker-icon">{r.symbol.slice(0, 2)}</span>
                  <span className="company-row-name">
                    <b>{r.symbol}</b>
                    <small>{r.data.company.name}</small>
                  </span>
                  <span className="company-row-price">
                    {r.data.quote
                      ? `${num(r.data.quote.price)} ${r.data.quote.currency}`
                      : "Sin cotización"}
                    <small>
                      {date(r.data.quote?.timestamp || r.created_at)}
                    </small>
                  </span>
                  <ArrowUpRight size={16} />
                </button>
              ))}
              {companies.length > 5 && (
                <button
                  className="list-more"
                  onClick={() => setShowAll(!showAll)}
                >
                  {showAll
                    ? "Mostrar menos"
                    : `Ver las ${companies.length} empresas`}
                  <ArrowRight size={14} />
                </button>
              )}
            </>
          ) : (
            <div className="dashboard-empty">
              <Search size={28} />
              <h4>Tu primera empresa empieza arriba</h4>
              <p>
                Aún no has consultado ninguna empresa. Busca por nombre o ticker
                para abrir su ficha.
              </p>
            </div>
          )}
        </section>

        <div className="dashboard-rail">
          <section
            className="panel recent-reports"
            aria-labelledby="recent-reports-title"
          >
            <div className="panel-heading">
              <h3 id="recent-reports-title">Tus investigaciones</h3>
              <FileText size={18} />
            </div>
            {!unavailable && reports.length ? (
              reports.map((r) => (
                <button
                  className="report-shortcut"
                  key={r.id}
                  disabled={props.busy}
                  onClick={() => props.onReport(r.id)}
                >
                  <span className="report-shortcut-icon">
                    <FileText size={18} />
                  </span>
                  <span>
                    <b>
                      {r.symbol}{" "}
                      <small>
                        {r.data.investment_horizon?.label ||
                          "Horizonte no registrado"}
                      </small>
                    </b>
                    <small>
                      {statusLabels[r.data.status] || "Estado no disponible"} ·{" "}
                      {date(r.created_at)}
                    </small>
                  </span>
                  <ArrowUpRight size={15} />
                </button>
              ))
            ) : (
              <p className="rail-empty">
                {unavailable
                  ? "La actividad aparecerá al completar la carga."
                  : "Tus expedientes aparecerán aquí al iniciar una investigación desde la ficha de una empresa."}
              </p>
            )}
            <button
              className="text-button"
              onClick={() => props.onNavigate("AI Investment Report")}
            >
              Abrir informes <ArrowRight size={14} />
            </button>
          </section>
          <section
            className="panel watch-preview"
            aria-labelledby="watch-preview-title"
          >
            <div className="panel-heading">
              <h3 id="watch-preview-title">En tu radar</h3>
              <Star size={18} />
            </div>
            {!unavailable && props.watch.length ? (
              <div className="watch-chips">
                {props.watch.slice(0, 6).map((r) => (
                  <button
                    key={r.id}
                    disabled={props.busy}
                    onClick={() => props.onLoad(r.symbol)}
                  >
                    {r.symbol}
                    <ArrowUpRight size={12} />
                  </button>
                ))}
              </div>
            ) : (
              <p className="rail-empty">
                {unavailable
                  ? "Cargando seguimiento…"
                  : "Guarda las empresas que quieres seguir y añade tus notas desde su ficha."}
              </p>
            )}
            <button
              className="text-button"
              onClick={() => props.onNavigate("Watchlist")}
            >
              Ver seguimiento <ArrowRight size={14} />
            </button>
          </section>
        </div>
      </div>
      <div className="local-ai-note">
        <span className="pending-dot" />
        <p>
          <b>Local AI research</b>
          <span>
            {props.localAIEnabled
              ? `Configured: ${props.localAIModel}. Check the connection in Settings; generation is not yet verified.`
              : "Use your Windows PC and LM Studio for local evidence analysis. Enable the local provider in the application configuration."}
          </span>
        </p>
        <button
          className="text-button"
          onClick={() => props.onNavigate("Settings")}
        >
          Ver configuración <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
