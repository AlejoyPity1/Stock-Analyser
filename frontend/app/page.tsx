"use client";
import WorkspaceHome from "../components/WorkspaceHome";
import SearchResults from "../components/SearchResults";
import {
  sectionLabels,
  horizonLabels,
  statusLabels,
} from "../components/workspace";
import RelativeValuation from "../components/RelativeValuation";
import FundamentalAnalytics from "../components/FundamentalAnalytics";
import MetricPanel from "../components/MetricPanel";
import FinancialStatements from "../components/FinancialStatements";
import ReportSections from "../components/ReportSections";
import HorizonSummary from "../components/HorizonSummary";
import ResearchFinancialFacts from "../components/ResearchFinancialFacts";
import ResearchTimingNotice from "../components/ResearchTimingNotice";
import CatalystBoard from "../components/CatalystBoard";
import PriceScenarios from "../components/PriceScenarios";
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  Database,
  FileText,
  FlaskConical,
  Globe,
  LayoutDashboard,
  LineChart,
  LoaderCircle,
  Menu,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Star,
  Target,
  Trash2,
  Users,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
  BarChart,
} from "recharts";
import { api, num, compact, pct, date, download } from "../components/api";
const sections = [
  ["Home", LayoutDashboard],
  ["Watchlist", Star],
  ["Stock Overview", Activity],
  ["Live Research", Globe],
  ["Scenarios", Target],
  ["Quantitative Analysis", LineChart],
  ["AI Investment Report", FileText],
  ["Financial Statements", Database],
  ["Valuation Lab", FlaskConical],
  ["Competitors", Users],
  ["Stock Screener", SlidersHorizontal],
  ["Settings", Settings2],
] as const;
const navGroups: Record<number, string> = {
  0: "TU ESPACIO",
  2: "ANÁLISIS",
  7: "HERRAMIENTAS",
  11: "PREFERENCIAS",
};
const researchSteps = [
  ["Stock Overview", "Empresa"],
  ["Live Research", "Investigación"],
  ["Scenarios", "Escenarios"],
  ["AI Investment Report", "Informe"],
];
const titles: Record<string, [string, string]> = {
  Home: [
    "Tu espacio de análisis.",
    "Investiga la acción que elijas con un horizonte principal de 3–6 meses.",
  ],
  "Stock Overview": [
    "La empresa, en perspectiva.",
    "Precio disponible, fundamentales y procedencia de los datos.",
  ],
  "Financial Statements": [
    "Los números detrás del negocio.",
    "Datos consolidados anuales de SEC EDGAR, con trazabilidad por partida.",
  ],
  "Valuation Lab": [
    "El precio es un dato. El valor, una hipótesis.",
    "Modela flujos de caja y haz explícitos tus supuestos.",
  ],
  "Live Research": [
    "Investiga los próximos 3–6 meses.",
    "Noticias, resultados y catalizadores; fundamentales como contexto.",
  ],
  Scenarios: [
    "Una tesis. Tres futuros posibles.",
    "Escenarios condicionales editables; sin probabilidades inventadas.",
  ],
  Competitors: [
    "Pon la valoración en contexto.",
    "Compara bases financieras y revisa la comparabilidad económica.",
  ],
  "Quantitative Analysis": [
    "Entiende el recorrido y el riesgo.",
    "Histórico de precios, comparación y riesgo, según la cobertura disponible.",
  ],
  "Stock Screener": [
    "Encuentra tu siguiente pregunta.",
    "Filtra el universo de empresas consultadas en esta instancia.",
  ],
  "AI Investment Report": [
    "De la evidencia a una tesis revisable.",
    "Informes guardados, citas y limitaciones explícitas.",
  ],
  Watchlist: [
    "Tus empresas, bajo seguimiento.",
    "Lista persistente y notas personales. Sin órdenes ni conexión a brokers.",
  ],
  Settings: [
    "Control sobre tus fuentes y tus costes.",
    "Estado de configuración del backend. Las claves nunca llegan al navegador.",
  ],
};
const fields: Record<string, string> = {
  revenue: "Ingresos",
  cost_revenue: "Coste de ventas",
  gross_profit: "Beneficio bruto",
  ebit: "EBIT",
  net_income: "Beneficio neto",
  eps: "EPS diluido",
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
function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="notice">
      <ShieldCheck size={17} />
      <div>{children}</div>
    </div>
  );
}
function Empty({
  text = "Busca una empresa para recuperar sus datos.",
  onSearch,
}: {
  text?: string;
  onSearch?: () => void;
}) {
  return (
    <div className="empty">
      <Database size={30} />
      <h3>La evidencia va primero</h3>
      <p>{text}</p>
      {onSearch && (
        <button className="secondary" onClick={onSearch}>
          Buscar empresa <ArrowRight size={15} />
        </button>
      )}
    </div>
  );
}
function Badge({
  children,
  good = false,
}: {
  children: React.ReactNode;
  good?: boolean;
}) {
  return <span className={"badge " + (good ? "good" : "")}>{children}</span>;
}
const initial = {
  revenue: "",
  growth: "5",
  operating_margin: "20",
  tax_rate: "21",
  capex_ratio: "5",
  da_ratio: "3",
  nwc_ratio: "10",
  wacc: "10",
  terminal_growth: "2.5",
  net_debt: "",
  shares: "",
  years: "5",
  price: "",
  currency: "USD",
  rationale: "Supuestos manuales del usuario; no son previsiones de consenso.",
};
const formFields = [
  ["revenue", "Ingresos base (millones)"],
  ["growth", "Crecimiento anual (%)"],
  ["operating_margin", "Margen operativo (%)"],
  ["tax_rate", "Tipo impositivo (%)"],
  ["capex_ratio", "Capex / ingresos (%)"],
  ["da_ratio", "D&A / ingresos (%)"],
  ["nwc_ratio", "NWC / ingresos (%)"],
  ["wacc", "WACC nominal (%)"],
  ["terminal_growth", "Crecimiento terminal (%)"],
  ["net_debt", "Deuda neta (millones)"],
  ["shares", "Acciones diluidas (millones)"],
  ["years", "Proyección (años)"],
  ["price", "Precio opcional / acción"],
];
function toInputs(form: Record<string, string>) {
  const m: any = {};
  for (const [k] of formFields) {
    if (k === "price" && !form[k]) {
      m.price = null;
      continue;
    }
    if (!form[k] || !Number.isFinite(Number(form[k])))
      throw Error("Completa los campos numéricos obligatorios.");
    m[k] = Number(form[k]);
    if (["revenue", "net_debt", "shares"].includes(k)) m[k] *= 1e6;
    else if (!["years", "price"].includes(k)) m[k] /= 100;
  }
  m.currency = form.currency;
  m.price_currency = m.price ? form.currency : null;
  m.rationale = form.rationale;
  return m;
}

export default function Page() {
  const [section, setSection] = useState("Home"),
    [nav, setNav] = useState(false),
    [query, setQuery] = useState(""),
    [matches, setMatches] = useState<any[]>([]),
    [data, setData] = useState<any>(null),
    [config, setConfig] = useState<any>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(""),
    [watch, setWatch] = useState<any[]>([]),
    [recent, setRecent] = useState<any[]>([]),
    [job, setJob] = useState<any>(null),
    [model, setModel] = useState<any>(null),
    [form, setForm] = useState<Record<string, string>>(initial),
    [useAI, setUseAI] = useState(false),
    [horizon, setHorizon] = useState("3-6m"),
    [budget, setBudget] = useState("0.10"),
    [history, setHistory] = useState<any>(null),
    [historyAdjusted, setHistoryAdjusted] = useState(false),
    [benchmark, setBenchmark] = useState(""),
    [peers, setPeers] = useState(""),
    [comparison, setComparison] = useState<any>(null),
    [screen, setScreen] = useState<any>(null),
    [maxPE, setMaxPE] = useState(""),
    [minYield, setMinYield] = useState(""),
    [minGrowth, setMinGrowth] = useState(""),
    [maxDebt, setMaxDebt] = useState(""),
    [screenIndustry, setScreenIndustry] = useState(""),
    [screenSort, setScreenSort] = useState("symbol"),
    [scenarioSaved, setScenarioSaved] = useState<any>(null),
    [scenarioHistory, setScenarioHistory] = useState<any[]>([]),
    [minMargin, setMinMargin] = useState(""),
    [saved, setSaved] = useState<any[]>([]),
    [versions, setVersions] = useState<any[]>([]),
    [sourceId, setSourceId] = useState(""),
    [parentId, setParentId] = useState<string | null>(null),
    [justification, setJustification] = useState(
      "Valoración inicial: supuestos manuales para revisión.",
    ),
    [scenarioForms, setScenarioForms] = useState<Record<
      string,
      Record<string, string>
    > | null>(null),
    [scenarios, setScenarios] = useState<any>(null),
    [scenarioTab, setScenarioTab] = useState("base"),
    [waccForm, setWaccForm] = useState({
      riskFree: 4,
      beta: 1,
      premium: 5,
      costDebt: 5,
      tax: 21,
      debtWeight: 20,
    });
  const searchRef = useRef<HTMLInputElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [localCheck, setLocalCheck] = useState<any>(null);
  const aiInitialized = useRef(false);
  const [workspaceError, setWorkspaceError] = useState(false);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k" &&
        !document.querySelector("dialog[open]")
      ) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => {
    if (!nav) return;
    const sidebar = sidebarRef.current!;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    sidebar.querySelector<HTMLButtonElement>(".sidebar-close")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setNav(false);
      }
      if (event.key !== "Tab") return;
      const controls = Array.from(
        sidebar.querySelectorAll<HTMLElement>("a[href], button:not(:disabled)"),
      ).filter((element) => element.getClientRects().length > 0);
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    const resize = () => {
      if (window.innerWidth > 760) setNav(false);
    };
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", resize);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", resize);
      previous?.focus();
    };
  }, [nav]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [section]);
  const symbol = data?.company?.symbol;
  async function refresh() {
    setWorkspaceLoading(true);
    setWorkspaceError(false);
    try {
      const [c, w, r, s] = await Promise.all([
        api("/settings"),
        api("/watchlist"),
        api("/records?kind=snapshot"),
        api("/records?kind=research"),
      ]);
      setConfig(c);
      if (!aiInitialized.current) {
        setUseAI(!!c.providers.local?.enabled);
        aiInitialized.current = true;
      }
      setWatch(w);
      setRecent(r);
      setSaved(s);
    } catch (e) {
      setWorkspaceError(true);
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setWorkspaceLoading(false);
    }
  }
  useEffect(() => {
    refresh();
  }, []);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const t = setInterval(async () => {
      try {
        const next = await api("/records/" + job.id);
        setJob(next);
        if (!["queued", "running"].includes(next.status)) refresh();
      } catch (e) {
        setError(String(e));
      }
    }, 1800);
    return () => clearInterval(t);
  }, [job?.id, job?.status]);
  async function perform(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  }
  async function find(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || busy) return;
    await perform("Buscando", async () => {
      const results = await api(
        "/search?q=" + encodeURIComponent(query.trim()),
      );
      setMatches(results);
      if (!results.length)
        setError("No se encontraron coincidencias en el universo SEC.");
    });
  }
  async function load(s: string) {
    await perform("Recuperando " + s, async () => {
      const d = await api("/companies/" + encodeURIComponent(s));
      setData(d);
      setMatches([]);
      setQuery(s);
      setHistory(null);
      setModel(null);
      setParentId(null);
      setJob(null);
      setSourceId("");
      setScenarios(null);
      setScenarioForms(null);
      setForm(initial);
      setSection("Stock Overview");
      setNav(false);
      setVersions(await api("/records?kind=valuation&symbol=" + s));
      setScenarioHistory(await api("/records?kind=scenario&symbol=" + s));
      setScenarioSaved(null);
      await refresh();
    });
  }
  async function research(mode: string) {
    if (!symbol) {
      setError("Selecciona una empresa primero.");
      return;
    }
    await perform("Iniciando investigación", async () => {
      setJob(
        await api("/research", {
          symbol,
          mode,
          horizon,
          use_ai: useAI,
          budget_usd: Number(budget),
        }),
      );
      setSection("Live Research");
    });
  }
  async function star(s: string, note = "") {
    await perform("Guardando", async () => {
      await api("/watchlist", { symbol: s, note });
      setWatch(await api("/watchlist"));
    });
  }
  function navigate(s: string) {
    setSection(s);
    setNav(false);
    setError("");
    if (s === "Stock Screener")
      perform("Cargando universo", async () => setScreen(await api("/screen")));
  }
  function prefill() {
    if (!data?.company?.statements?.length) {
      setError("No hay un ejercicio anual disponible.");
      return;
    }
    const v = data.company.statements[0].values;
    const metrics = data.metrics;
    setForm({
      ...initial,
      revenue: v.revenue ? String(v.revenue.value / 1e6) : "",
      net_debt: metrics.net_debt != null ? String(metrics.net_debt / 1e6) : "",
      shares:
        v.shares && !data.company.multiple_share_classes
          ? String(v.shares.value / 1e6)
          : "",
      operating_margin:
        metrics.operating_margin != null
          ? String(metrics.operating_margin * 100)
          : "",
      capex_ratio: v.capex
        ? String((v.capex.value / v.revenue.value) * 100)
        : "",
      da_ratio: v.da ? String((v.da.value / v.revenue.value) * 100) : "",
      price:
        data.quote?.currency === data.company.currency
          ? String(data.quote.price)
          : "",
      currency: data.company.currency,
    });
    setModel(null);
  }
  async function calculate(save = false) {
    await perform("Calculando", async () => {
      const inputs = toInputs(form);
      if (save) {
        if (!symbol)
          throw Error("Selecciona una empresa para guardar la valoración.");
        const result = await api("/valuations", {
          symbol,
          inputs,
          parent_id: parentId,
          source_id: sourceId || null,
          research_id: sourceId ? job?.id : null,
          justification,
        });
        setModel(result);
        setParentId(result.id);
        setVersions(await api("/records?kind=valuation&symbol=" + symbol));
      } else setModel(await api("/valuation/preview", inputs));
    });
  }
  async function exportReport() {
    if (!job?.id) return;
    await perform("Exportando", async () =>
      download(
        "informe-" + job.symbol + ".json",
        await api("/reports/" + job.id),
      ),
    );
  }
  function projectionChart(rows: any[]) {
    return (
      <div className="chart">
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={rows}>
            <CartesianGrid stroke="#26303b" vertical={false} />
            <XAxis dataKey="year" stroke="#77838d" />
            <YAxis
              tickFormatter={(v) => compact(v)}
              stroke="#77838d"
              width={65}
            />
            <Tooltip
              contentStyle={{ background: "#171d25", border: "1px solid #333" }}
              formatter={(v) => compact(v)}
            />
            <Bar
              dataKey="fcff"
              name="FCFF"
              fill="#afc9ab"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }
  function sourceList() {
    return (
      <div className="source-list">
        {job?.sources?.map((s: any) => (
          <article className="source" key={s.id}>
            <div className="row">
              <Badge good={s.read_status === "read"}>
                {s.read_status === "read"
                  ? s.full_text
                    ? "Documento leído"
                    : "Lectura truncada"
                  : s.read_status === "abstract_only"
                    ? "Solo extracto"
                    : s.read_status === "inaccessible"
                      ? "Inaccesible"
                      : "Sin leer"}
              </Badge>
              <span className="muted">
                {s.publisher} · {date(s.published_at)}
              </span>
            </div>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title}
              <ArrowUpRight size={15} />
            </a>
            {s.summary && <p>{s.summary}</p>}
            <small>
              ID: {s.id} · Recuperado: {date(s.retrieved_at)}
            </small>
            {s.error && <p className="error-text">{s.error}</p>}
            {s.text && (
              <details>
                <summary>
                  Texto recuperado · {s.text.length.toLocaleString("es-ES")}{" "}
                  caracteres
                </summary>
                <pre>{s.text}</pre>
              </details>
            )}
            <p className="muted">
              Impacto en modelo: pendiente de revisión. No se han modificado
              supuestos.
            </p>
          </article>
        ))}
      </div>
    );
  }
  const modelDirty =
    !!model &&
    (() => {
      try {
        return Object.entries(toInputs(form)).some(
          ([k, v]) => JSON.stringify(v) !== JSON.stringify(model.inputs[k]),
        );
      } catch {
        return true;
      }
    })();
  const heading = titles[section];
  const contextSymbol =
    section === "AI Investment Report" ? job?.symbol : symbol;
  const contextHorizon =
    job?.symbol === contextSymbol &&
    ["AI Investment Report", "Live Research"].includes(section)
      ? job?.investment_horizon?.label || "Horizonte no registrado"
      : horizonLabels[horizon];
  async function openReport(id: string) {
    await perform("Abriendo informe", async () => {
      setJob(await api("/records/" + id));
      navigate("AI Investment Report");
    });
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace-content">
        Saltar al contenido
      </a>
      {nav && (
        <button
          className="nav-backdrop"
          tabIndex={-1}
          aria-label="Cerrar menú de navegación"
          onClick={() => setNav(false)}
        />
      )}
      <aside
        ref={sidebarRef}
        id="workspace-navigation"
        aria-label="Menú principal"
        className={"sidebar " + (nav ? "open" : "")}
      >
        <div className="sidebar-brand-row">
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate("Home");
            }}
          >
            <span className="brand-icon">
              <Activity size={23} />
            </span>
            <span>
              stock<span className="brand-light">intelligence</span>
              <small>INVESTIGA. CONECTA. DECIDE.</small>
            </span>
          </a>
          <button
            className="icon sidebar-close"
            aria-label="Cerrar navegación"
            onClick={() => setNav(false)}
          >
            <X size={20} />
          </button>
        </div>
        <nav aria-label="Navegación principal">
          {sections.map(([s, Icon], i) => (
            <div key={s}>
              {navGroups[i] && (
                <div className="sidebar-label">{navGroups[i]}</div>
              )}
              <button
                className={section === s ? "active" : ""}
                aria-current={section === s ? "page" : undefined}
                onClick={() => navigate(s)}
              >
                <Icon size={18} />
                <span>{sectionLabels[s]}</span>
                {s === "Watchlist" && <small>{watch.length}</small>}
                {s === "Live Research" &&
                  ["queued", "running"].includes(job?.status) && (
                    <span
                      className="nav-dot"
                      aria-label="Investigación en curso"
                    />
                  )}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="row">
            <ShieldCheck size={18} />
            <b>Evidencia antes que opinión</b>
          </div>
          <p>
            Fuentes visibles. Cálculos reproducibles.
            <br />
            Incertidumbre explícita.
          </p>
          <div className="profile">
            <span>SI</span>
            <div>
              Espacio personal<small>Stock Intelligence AI</small>
            </div>
            <Settings2 size={15} />
          </div>
        </div>
      </aside>
      <main inert={nav}>
        <header className="topbar">
          <button
            className="icon mobile-menu"
            aria-label="Abrir navegación"
            aria-expanded={nav}
            aria-controls="workspace-navigation"
            onClick={() => setNav(!nav)}
          >
            <Menu size={20} />
          </button>
          <span className="breadcrumb">
            Mi espacio <ChevronRight size={13} />{" "}
            <b>{sectionLabels[section]}</b>
          </span>
          <form className="search" role="search" onSubmit={find}>
            <Search size={16} />
            <input
              ref={searchRef}
              aria-label="Buscar empresa o ticker"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar empresa o ticker…"
            />
            <kbd aria-hidden="true">Ctrl K</kbd>
            <button
              type="submit"
              aria-label="Ejecutar búsqueda"
              disabled={!!busy || !query.trim()}
            >
              <ArrowRight size={16} />
            </button>
          </form>
          <span className="data-label">
            <Target size={15} /> ENFOQUE 3–6 MESES
          </span>
        </header>
        {matches.length > 0 && (
          <SearchResults
            matches={matches}
            query={query.trim()}
            busy={!!busy}
            error={error}
            onClose={() => setMatches([])}
            onSelect={load}
          />
        )}
        <div className="page" id="workspace-content" tabIndex={-1}>
          <div className="page-eyebrow">
            <span className="tiny-line" />
            {section === "Home"
              ? "INVESTIGACIÓN DE ACCIONES"
              : sectionLabels[section].toUpperCase()}
            <span className="muted">/ ESPACIO PERSONAL</span>
          </div>
          <div className="page-heading">
            <div>
              <h1>{heading[0]}</h1>
              <p>{heading[1]}</p>
            </div>
            {contextSymbol && (
              <div className="company-chip">
                <span>{contextSymbol.slice(0, 2)}</span>
                <div>
                  <b>{contextSymbol}</b>
                  <small>{contextHorizon}</small>
                </div>
              </div>
            )}
          </div>
          {error && (
            <div role="alert" className="error-banner">
              <span>{error}</span>
              <button
                className="icon"
                aria-label="Cerrar error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {busy && (
            <div className="loading" role="status">
              <LoaderCircle size={16} className="spin" />
              {busy}…
            </div>
          )}
          {symbol &&
            section !== "Home" &&
            section !== "Settings" &&
            section !== "Watchlist" &&
            !(section === "AI Investment Report" && job?.symbol !== symbol) && (
              <nav className="analysis-trail" aria-label="Pasos del análisis">
                <span className="trail-company">
                  {symbol}
                  <small>Tu recorrido</small>
                </span>
                {researchSteps.map(([destination, label], index) => (
                  <button
                    key={destination}
                    aria-label={`Paso ${index + 1}: ${label}`}
                    aria-current={section === destination ? "step" : undefined}
                    className={section === destination ? "current" : ""}
                    onClick={() => navigate(destination)}
                  >
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    {label}
                    <ChevronRight size={14} />
                  </button>
                ))}
              </nav>
            )}
          {section === "Home" && (
            <WorkspaceHome
              query={query}
              onQuery={setQuery}
              onSearch={find}
              onLoad={load}
              onNavigate={navigate}
              onReport={openReport}
              recent={recent}
              reports={saved}
              watch={watch}
              horizon={horizon}
              onHorizon={setHorizon}
              busy={!!busy}
              loading={workspaceLoading}
              loadError={workspaceError}
              localAIEnabled={!!config?.providers.local?.enabled}
              localAIModel={config?.providers.local?.model || "qwen/qwen3.5-9b"}
              onRetry={() => {
                setError("");
                void refresh();
              }}
            />
          )}
          {section === "Stock Overview" &&
            (data ? (
              <>
                <div className="company-title">
                  <h2>{data.company.name}</h2>
                  <button
                    className="secondary"
                    disabled={!!busy || watch.some((w) => w.symbol === symbol)}
                    onClick={() => star(symbol)}
                  >
                    <Star
                      size={15}
                      fill={
                        watch.some((w) => w.symbol === symbol)
                          ? "currentColor"
                          : "none"
                      }
                    />{" "}
                    {watch.some((w) => w.symbol === symbol)
                      ? "En seguimiento"
                      : "Seguir empresa"}
                  </button>
                </div>
                <p className="muted">
                  {data.company.industry} · CIK {data.company.cik} · Recuperado{" "}
                  {date(data.company.retrieved_at)}
                </p>
                <div className="metrics-grid">
                  {[
                    [
                      "Último precio disponible",
                      data.quote
                        ? `${num(data.quote.price)} ${data.quote.currency}`
                        : "No disponible",
                      data.quote
                        ? date(data.quote.timestamp)
                        : "Requiere proveedor de mercado",
                    ],
                    [
                      "Ingresos anuales",
                      compact(
                        data.company.statements[0]?.values.revenue?.value,
                      ),
                      data.company.statements[0]?.end || "Sin ejercicio",
                    ],
                    [
                      "Free cash flow",
                      compact(data.metrics.free_cash_flow),
                      "OCF − capex · moneda de reporte",
                    ],
                    [
                      "Margen operativo",
                      pct(data.metrics.operating_margin),
                      "EBIT / ingresos anuales",
                    ],
                  ].map(([a, b, c]) => (
                    <div className="metric" key={a}>
                      <span>{a}</span>
                      <strong>{b}</strong>
                      <small>{c}</small>
                    </div>
                  ))}
                </div>
                <Notice>
                  {data.quote
                    ? "Cotización más reciente disponible, sin garantía de tiempo real. " +
                      (data.quote.stale ? "Dato de más de 24 horas." : "")
                    : "No se ha recuperado una cotización. No se calcula upside sin precio."}{" "}
                  Los estados son anuales, no TTM.
                </Notice>
                <div className="action-grid">
                  <button
                    className="action-card"
                    disabled={
                      !!busy || ["queued", "running"].includes(job?.status)
                    }
                    onClick={() => research("quick")}
                  >
                    <Globe />
                    <h3>Investigación rápida</h3>
                    <p>
                      Fuentes recientes y documentos oficiales para tu horizonte
                      de inversión. Hasta 10 publicaciones disponibles.
                    </p>
                    <span>
                      Iniciar investigación <ArrowRight size={16} />
                    </span>
                  </button>
                  <button
                    className="action-card"
                    disabled={
                      !!busy || ["queued", "running"].includes(job?.status)
                    }
                    onClick={() => research("deep")}
                  >
                    <BookOpen />
                    <h3>Investigación profunda</h3>
                    <p>
                      Mayor lectura de documentos para el mismo horizonte.
                      Consulta antecedentes de 30, 90 y 365 días, según
                      cobertura.
                    </p>
                    <span>
                      Investigar en profundidad <ArrowRight size={16} />
                    </span>
                  </button>
                  <button
                    className="action-card"
                    onClick={() => {
                      navigate("Scenarios");
                    }}
                  >
                    <Target />
                    <h3>Escenarios a 3–6 meses</h3>
                    <p>
                      Compara precios condicionales, retornos y condiciones que
                      invalidarían tus hipótesis.
                    </p>
                    <span>
                      Construir escenarios <ArrowRight size={16} />
                    </span>
                  </button>
                </div>
                <MetricPanel key={symbol} data={data} />
                <FundamentalAnalytics analytics={data.analytics} />
                {[
                  ...data.warnings.map((w: any) => w.message),
                  ...data.company.limitations,
                ].map((w: string) => (
                  <p className="footnote" key={w}>
                    {w}
                  </p>
                ))}
              </>
            ) : (
              <Empty onSearch={() => searchRef.current?.focus()} />
            ))}
          {section === "Financial Statements" &&
            (data ? (
              <FinancialStatements key={symbol} company={data.company} />
            ) : (
              <Empty onSearch={() => searchRef.current?.focus()} />
            ))}
          {section === "Valuation Lab" && (
            <>
              <Notice>
                Los porcentajes iniciales son hipótesis editables, no
                estimaciones financieras reales. El DCF FCFF genérico no es
                adecuado para bancos, aseguradoras o REITs. Usa un modelo
                sectorial antes de sacar conclusiones.
              </Notice>
              <div className="valuation-grid">
                <section className="panel">
                  <div className="panel-heading">
                    <h3>Hipótesis del modelo</h3>
                    <button className="text-button" onClick={prefill}>
                      Usar último ejercicio <ArrowDownToLine size={14} />
                    </button>
                  </div>
                  <div className="form-grid">
                    {formFields.map(([k, label]) => (
                      <label key={k}>
                        {label}
                        <input
                          type="number"
                          step="any"
                          value={form[k]}
                          onChange={(e) =>
                            setForm({ ...form, [k]: e.target.value })
                          }
                          required={k !== "price"}
                        />
                      </label>
                    ))}
                    <label>
                      Divisa de todos los importes
                      <input
                        value={form.currency}
                        maxLength={3}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            currency: e.target.value.toUpperCase(),
                          })
                        }
                      />
                    </label>
                  </div>
                  <label>
                    Fundamento de los supuestos
                    <textarea
                      aria-label="Fundamento de los supuestos"
                      value={form.rationale}
                      onChange={(e) =>
                        setForm({ ...form, rationale: e.target.value })
                      }
                    />
                  </label>
                  <div className="buttons">
                    <button
                      className="primary"
                      onClick={() => calculate()}
                      disabled={!!busy}
                    >
                      Calcular DCF <ArrowRight size={15} />
                    </button>
                    <button
                      className="secondary"
                      onClick={() => calculate(true)}
                      disabled={!!busy}
                    >
                      Guardar versión
                    </button>
                  </div>
                  <details className="advanced">
                    <summary>Auditoría de cambios y WACC</summary>
                    <label>
                      Justificación de la versión
                      <textarea
                        aria-label="Justificación de la versión"
                        value={justification}
                        onChange={(e) => setJustification(e.target.value)}
                      />
                    </label>
                    <label>
                      Fuente de la investigación actual
                      <select
                        value={sourceId}
                        onChange={(e) => setSourceId(e.target.value)}
                      >
                        <option value="">
                          Sin noticia asociada · hipótesis manual
                        </option>
                        {job?.sources
                          ?.filter((s: any) =>
                            ["read", "abstract_only"].includes(s.read_status),
                          )
                          .map((s: any) => (
                            <option value={s.id} key={s.id}>
                              {s.title}
                            </option>
                          ))}
                      </select>
                    </label>
                    <p className="muted">
                      Guardar una nueva versión desde una versión guardada
                      registra diferencias y efecto en valor.
                    </p>
                    <div className="form-grid">
                      {Object.entries(waccForm).map(([k, v]) => (
                        <label key={k}>
                          {
                            (
                              {
                                riskFree: "Tasa libre de riesgo %",
                                beta: "Beta",
                                premium: "Prima de equity %",
                                costDebt: "Coste de deuda %",
                                tax: "Impuestos %",
                                debtWeight: "Peso de deuda %",
                              } as any
                            )[k]
                          }
                          <input
                            type="number"
                            value={v}
                            onChange={(e) =>
                              setWaccForm({
                                ...waccForm,
                                [k]: Number(e.target.value),
                              })
                            }
                          />
                        </label>
                      ))}
                    </div>
                    <button
                      className="secondary"
                      onClick={() => {
                        if (
                          waccForm.debtWeight < 0 ||
                          waccForm.debtWeight > 100 ||
                          waccForm.tax < 0 ||
                          waccForm.tax > 100
                        ) {
                          setError("Pesos y tasa deben estar entre 0% y 100%.");
                          return;
                        }
                        setForm({
                          ...form,
                          wacc: String(
                            (waccForm.riskFree +
                              waccForm.beta * waccForm.premium) *
                              (1 - waccForm.debtWeight / 100) +
                              (waccForm.costDebt *
                                (1 - waccForm.tax / 100) *
                                waccForm.debtWeight) /
                                100,
                          ),
                        });
                      }}
                    >
                      Aplicar CAPM + coste de deuda
                    </button>
                    <p className="muted">
                      WACC = (Rf + β × ERP) × E/(D+E) + Kd × (1−T) × D/(D+E).
                      Inputs manuales.
                    </p>
                  </details>
                </section>
                <section className="panel results">
                  <div className="panel-heading">
                    <h3>Valor intrínseco presente</h3>
                    <Badge>FCFF · v1.0</Badge>
                  </div>
                  {model ? (
                    <>
                      {modelDirty && (
                        <Notice>
                          Hay cambios sin recalcular. Los resultados
                          corresponden a la última ejecución guardada en esta
                          vista.
                        </Notice>
                      )}
                      <div className="fair-value">
                        {num(model.fair_value)}{" "}
                        <small>{model.currency} / acción</small>
                      </div>
                      <div className="result-line">
                        <span>Upside / downside</span>
                        <b>{pct(model.upside)}</b>
                      </div>
                      <div className="result-line">
                        <span>Margen de seguridad (1 − precio/valor)</span>
                        <b>{pct(model.margin_of_safety)}</b>
                      </div>
                      <div className="result-line">
                        <span>Enterprise Value</span>
                        <b>{compact(model.enterprise_value)}</b>
                      </div>
                      <div className="result-line">
                        <span>Equity Value</span>
                        <b>{compact(model.equity_value)}</b>
                      </div>
                      {projectionChart(model.projections)}
                      <p className="formula">{model.formula}</p>
                      {model.warnings.map((w: string) => (
                        <Notice key={w}>{w}</Notice>
                      ))}
                      <h3>Reverse DCF</h3>
                      <p>
                        {model.reverse_dcf?.growth != null
                          ? `Crecimiento implícito: ${pct(model.reverse_dcf.growth)}. ${model.reverse_dcf.interpretation}`
                          : model.reverse_dcf?.reason}
                      </p>
                      <h3>Sensibilidad WACC / g terminal</h3>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>WACC ↓ / g →</th>
                              {model.sensitivity.terminal_growth.map(
                                (g: number) => (
                                  <th key={g}>{pct(g)}</th>
                                ),
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {model.sensitivity.rows.map((r: any) => (
                              <tr key={r.wacc}>
                                <td>{pct(r.wacc)}</td>
                                {r.values.map((v: number, i: number) => (
                                  <td key={i}>{num(v)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {model.changes?.length > 0 && (
                        <details>
                          <summary>
                            Cambios guardados · efecto {num(model.value_effect)}{" "}
                            / acción
                          </summary>
                          <pre>{JSON.stringify(model.changes, null, 2)}</pre>
                        </details>
                      )}
                    </>
                  ) : (
                    <Empty text="Introduce datos base y supuestos para calcular una valoración reproducible. El cálculo funciona sin servicios de pago." />
                  )}
                </section>
              </div>
              {versions.length > 0 && (
                <section className="panel">
                  <h3>Versiones guardadas</h3>
                  {versions.map((v) => (
                    <button
                      key={v.id}
                      className="saved-row"
                      onClick={() => {
                        setModel(v.data);
                        setParentId(v.id);
                        const f: any = { ...initial, ...v.data.inputs };
                        for (const [k] of formFields) {
                          const val = v.data.inputs[k];
                          f[k] =
                            val == null
                              ? ""
                              : String(
                                  ["revenue", "shares", "net_debt"].includes(k)
                                    ? val / 1e6
                                    : ["price", "years"].includes(k)
                                      ? val
                                      : val * 100,
                                );
                        }
                        setForm(f);
                      }}
                    >
                      <span>{date(v.created_at)}</span>
                      <b>
                        {num(v.data.fair_value)} {v.data.currency}
                      </b>
                      <span>{v.data.justification}</span>
                      <ChevronRight size={16} />
                    </button>
                  ))}
                </section>
              )}
            </>
          )}
          {section === "Live Research" && (
            <>
              <div className="research-controls">
                <label>
                  Horizonte de inversión
                  <select
                    aria-label="Horizonte de inversión"
                    value={horizon}
                    onChange={(e) => setHorizon(e.target.value)}
                  >
                    <option value="3-6m">3–6 meses</option>
                    <option value="3m">3 meses</option>
                    <option value="6m">6 meses</option>
                  </select>
                </label>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={useAI}
                    disabled={
                      !config?.providers.local?.enabled &&
                      !config?.providers.openai.enabled
                    }
                    onChange={(e) => setUseAI(e.target.checked)}
                  />{" "}
                  Use AI for evidence analysis
                </label>
                {config?.providers.local?.enabled && (
                  <span className="badge good">
                    Local · {config.providers.local.model}
                  </span>
                )}
                {config?.providers.openai.enabled && (
                  <label>
                    Presupuesto máximo USD{" "}
                    <input
                      className="budget"
                      type="number"
                      min="0.01"
                      max="5"
                      step=".01"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                    />
                  </label>
                )}
                <button
                  className="secondary"
                  onClick={() => research("quick")}
                  disabled={
                    !!busy || ["queued", "running"].includes(job?.status)
                  }
                >
                  Investigación rápida
                </button>
                <button
                  className="primary"
                  onClick={() => research("deep")}
                  disabled={
                    !!busy || ["queued", "running"].includes(job?.status)
                  }
                >
                  Investigación profunda <BookOpen size={16} />
                </button>
              </div>
              <Notice>
                Quick and Deep change research depth, not the investment
                horizon. Local AI analyzes bounded excerpts in English and
                checks literal quotations. Source coverage and omissions are
                recorded. Model interpretation requires review; quotations alone
                do not establish a complete investment thesis.
              </Notice>
              {job ? (
                <>
                  <section className="panel">
                    <div className="panel-heading">
                      <h3>
                        {job.symbol} ·{" "}
                        {job.request.mode === "deep"
                          ? "Investigación profunda"
                          : "Investigación rápida"}
                      </h3>
                      <Badge good={job.status === "completed"}>
                        {statusLabels[job.status] || job.status}
                      </Badge>
                    </div>
                    <div className="row">
                      <Activity size={16} />
                      <b>{job.stage}</b>
                      {["running", "queued"].includes(job.status) && (
                        <button
                          className="text-button"
                          onClick={() =>
                            perform("Cancelando", async () =>
                              setJob(
                                await api(
                                  "/research/" + job.id + "/cancel",
                                  {},
                                ),
                              ),
                            )
                          }
                        >
                          Cancelar
                        </button>
                      )}
                    </div>
                    <p className="muted">
                      Inicio {date(job.created_at)} · Última actualización{" "}
                      {date(job.updated_at)}
                    </p>
                    <HorizonSummary horizon={job.investment_horizon} />
                    <ResearchTimingNotice quality={job.ai?.data?.quality_control} />
                    {job.error && <p className="error-text">{job.error}</p>}
                    {job.stats && (
                      <div className="stats">
                        {Object.entries(job.stats).map(([k, v]) => (
                          <div key={k}>
                            <b>{v == null ? "Sin evaluar" : String(v)}</b>
                            <span>{k.replaceAll("_", " ")}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {job.errors?.map((e: any, i: number) => (
                      <p className="error-text" key={i}>
                        {e.provider}: {e.message}
                      </p>
                    ))}
                    {job.ai && (
                      <p className="muted">
                        IA: {job.ai.status} {job.ai.reason}
                      </p>
                    )}
                    <button
                      className="text-button"
                      onClick={() => navigate("AI Investment Report")}
                    >
                      Abrir expediente e informe <ArrowRight size={16} />
                    </button>
                  </section>
                  {sourceList()}
                </>
              ) : (
                <Empty text="Selecciona una empresa e inicia una investigación rápida o profunda para recopilar sus fuentes." />
              )}
              <CatalystBoard symbol={symbol} research={job} />
            </>
          )}
          {section === "Scenarios" && (
            <>
              <PriceScenarios
                symbol={symbol}
                quote={data?.quote}
                research={job}
              />
              <h3>Escenarios DCF · contexto de valor presente</h3>
              <Notice>
                Los escenarios son hipótesis condicionales. El valor mostrado es
                presente; no se presenta como predicción bursátil a 3 o 6 meses.
                Edita y justifica cada caso.
              </Notice>
              <button
                className="secondary"
                onClick={() => {
                  setScenarioForms({
                    bear: {
                      ...form,
                      rationale:
                        "Hipótesis bajista manual: revisar riesgos y evidencia.",
                    },
                    base: { ...form },
                    bull: {
                      ...form,
                      rationale:
                        "Hipótesis alcista manual: revisar catalizadores y evidencia.",
                    },
                  });
                  setScenarios(null);
                }}
              >
                Copiar hipótesis del DCF
              </button>
              {scenarioForms && (
                <>
                  <div className="tabs">
                    {["bear", "base", "bull"].map((k) => (
                      <button
                        className={scenarioTab === k ? "selected" : ""}
                        key={k}
                        onClick={() => setScenarioTab(k)}
                      >
                        {k.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  <section className="panel">
                    <div className="form-grid">
                      {formFields.map(([k, l]) => (
                        <label key={k}>
                          {l}
                          <input
                            type="number"
                            step="any"
                            value={scenarioForms[scenarioTab][k]}
                            onChange={(e) =>
                              setScenarioForms({
                                ...scenarioForms,
                                [scenarioTab]: {
                                  ...scenarioForms[scenarioTab],
                                  [k]: e.target.value,
                                },
                              })
                            }
                          />
                        </label>
                      ))}
                    </div>
                    <label>
                      Hipótesis, riesgos y catalizadores
                      <textarea
                        value={scenarioForms[scenarioTab].rationale}
                        onChange={(e) =>
                          setScenarioForms({
                            ...scenarioForms,
                            [scenarioTab]: {
                              ...scenarioForms[scenarioTab],
                              rationale: e.target.value,
                            },
                          })
                        }
                      />
                    </label>
                    <button
                      className="primary"
                      onClick={() =>
                        perform("Calculando escenarios", async () =>
                          setScenarios(
                            await api(
                              "/scenarios",
                              Object.fromEntries(
                                Object.entries(scenarioForms).map(([k, v]) => [
                                  k,
                                  toInputs(v),
                                ]),
                              ),
                            ),
                          ),
                        )
                      }
                    >
                      Calcular los tres escenarios
                    </button>
                    <button
                      className="secondary"
                      disabled={!symbol || !!busy}
                      onClick={() =>
                        perform("Guardando escenarios", async () => {
                          const saved = await api("/scenario-sets", {
                            symbol,
                            ...Object.fromEntries(
                              Object.entries(scenarioForms).map(([k, v]) => [
                                k,
                                toInputs(v),
                              ]),
                            ),
                            research_id: job?.symbol === symbol ? job.id : null,
                            justification:
                              "Escenarios manuales: " +
                              scenarioForms.base.rationale,
                          });
                          setScenarios(saved.results);
                          setScenarioSaved(saved);
                          setScenarioHistory(
                            await api(
                              "/records?kind=scenario&symbol=" + symbol,
                            ),
                          );
                        })
                      }
                    >
                      Guardar escenarios
                    </button>
                    {scenarioSaved && (
                      <p className="muted">
                        Escenarios guardados · {date(scenarioSaved.created_at)}
                      </p>
                    )}
                  </section>
                </>
              )}
              {scenarios && (
                <div className="action-grid">
                  {Object.entries(scenarios).map(([k, s]: [string, any]) => (
                    <section className="panel" key={k}>
                      <Badge>{k.toUpperCase()}</Badge>
                      <div className="fair-value">
                        {num(s.fair_value)}
                        <small>{s.currency} / acción</small>
                      </div>
                      <p>Upside {pct(s.upside)}</p>
                      <p>{s.inputs.rationale}</p>
                      {projectionChart(s.projections)}
                    </section>
                  ))}
                </div>
              )}
            </>
          )}
          {section === "Scenarios" && scenarioHistory.length > 0 && (
            <section className="panel">
              <h3>Historial de escenarios</h3>
              {scenarioHistory.map((r) => (
                <button
                  className="saved-row"
                  key={r.id}
                  onClick={() => {
                    setScenarios(r.data.results);
                    setScenarioSaved(r.data);
                    const forms: any = {};
                    for (const [k, input] of Object.entries(r.data.inputs) as [
                      string,
                      any,
                    ][]) {
                      const f: any = { ...initial, ...input };
                      for (const [field] of formFields) {
                        const val = input[field];
                        f[field] =
                          val == null
                            ? ""
                            : String(
                                ["revenue", "net_debt", "shares"].includes(
                                  field,
                                )
                                  ? val / 1e6
                                  : ["price", "years"].includes(field)
                                    ? val
                                    : val * 100,
                              );
                      }
                      forms[k] = f;
                    }
                    setScenarioForms(forms);
                  }}
                >
                  <span>{date(r.created_at)}</span>
                  <span>{r.data.justification}</span>
                </button>
              ))}
            </section>
          )}
          {section === "Competitors" && (
            <>
              <form
                className="inline-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  perform("Comparando empresas", async () =>
                    setComparison(
                      await api(
                        "/compare?symbols=" + encodeURIComponent(peers),
                      ),
                    ),
                  );
                }}
              >
                <label>
                  De 2 a 5 tickers, separados por coma
                  <input
                    value={peers}
                    onChange={(e) => setPeers(e.target.value)}
                    placeholder="AAPL, MSFT"
                  />
                </label>
                <button className="primary">
                  Comparar <Users size={15} />
                </button>
              </form>
              {comparison ? (
                <section className="panel">
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Empresa</th>
                          <th>Divisa / período</th>
                          <th>Industria</th>
                          <th>P/E</th>
                          <th>EV / EBITDA</th>
                          <th>Margen EBIT</th>
                          <th>FCF yield</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparison.rows.map((r: any) => (
                          <tr key={r.symbol}>
                            <td>
                              {r.symbol}
                              <small>{r.error || r.name}</small>
                            </td>
                            <td>
                              {r.currency} / {r.period}
                              <small>
                                Cotización:{" "}
                                {r.quote_currency || "no disponible"}
                              </small>
                              {r.quote_currency &&
                                r.quote_currency !== r.currency && (
                                  <small className="error-text">
                                    Divisas distintas: múltiplos no calculados
                                  </small>
                                )}
                            </td>
                            <td>{r.industry}</td>
                            <td>{num(r.metrics?.pe)}</td>
                            <td>{num(r.metrics?.ev_ebitda)}</td>
                            <td>{pct(r.metrics?.operating_margin)}</td>
                            <td>{pct(r.metrics?.fcf_yield)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {comparison.limitations.map((l: string) => (
                    <p className="muted" key={l}>
                      {l}
                    </p>
                  ))}
                </section>
              ) : (
                <Empty text="La comparación consulta empresas reales. Los múltiplos requieren precios en la misma divisa que los estados." />
              )}
            </>
          )}
          {section === "Competitors" && (
            <RelativeValuation
              symbol={symbol}
              researchId={job && job.symbol === symbol ? job.id : undefined}
            />
          )}
          {section === "Quantitative Analysis" && (
            <>
              <div className="inline-form">
                <label>
                  Tipo de serie
                  <select
                    value={String(historyAdjusted)}
                    onChange={(e) =>
                      setHistoryAdjusted(e.target.value === "true")
                    }
                  >
                    <option value="false">
                      Precios SIN ajustar · opción disponible
                    </option>
                    <option value="true">
                      Precios ajustados · según plan del proveedor
                    </option>
                  </select>
                </label>
                <label>
                  Benchmark opcional (ticker US)
                  <input
                    value={benchmark}
                    onChange={(e) => setBenchmark(e.target.value.toUpperCase())}
                    placeholder="Por ejemplo, SPY"
                  />
                </label>
                <button
                  className="primary"
                  disabled={!symbol || !!busy}
                  onClick={() =>
                    perform("Recuperando histórico", async () =>
                      setHistory(
                        await api(
                          "/companies/" +
                            symbol +
                            "/history?" +
                            new URLSearchParams({
                              adjusted: String(historyAdjusted),
                              ...(benchmark ? { benchmark } : {}),
                            }),
                        ),
                      ),
                    )
                  }
                >
                  Recuperar histórico <LineChart size={16} />
                </button>
              </div>
              <Notice>
                La serie sin ajustar se elige explícitamente y no corrige splits
                ni dividendos. Puede distorsionar retornos e indicadores. La
                serie ajustada depende de los derechos del plan. Sin fallback
                silencioso. Cobertura compacta: hasta 100 sesiones, MA200 no
                disponible sin suficiente historial.
              </Notice>
              {history ? (
                <section className="panel">
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={history.points}>
                      <defs>
                        <linearGradient id="price" x1="0" y1="0" x2="0" y2="1">
                          <stop
                            offset="0%"
                            stopColor="#afc9ab"
                            stopOpacity={0.3}
                          />
                          <stop
                            offset="100%"
                            stopColor="#afc9ab"
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#26303b" vertical={false} />
                      <XAxis dataKey="date" minTickGap={60} stroke="#77838d" />
                      <YAxis domain={["auto", "auto"]} stroke="#77838d" />
                      <Tooltip contentStyle={{ background: "#171d25" }} />
                      <Area
                        dataKey={history.adjusted ? "adjusted_close" : "close"}
                        stroke="#afc9ab"
                        fill="url(#price)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                  <div className="ratio-grid">
                    {Object.entries(history.metrics)
                      .filter(([k]) => k !== "methodology")
                      .map(([k, v]) => (
                        <div key={k}>
                          <span>{k}</span>
                          <b>{num(v)}</b>
                        </div>
                      ))}
                  </div>
                  <p className="muted">
                    {history.metrics.methodology} {history.adjustment}
                  </p>
                  {history.benchmark && (
                    <div>
                      <h3>Comparación con {history.benchmark.symbol}</h3>
                      <div className="ratio-grid">
                        {Object.entries(history.benchmark)
                          .filter(([k]) =>
                            [
                              "beta",
                              "correlation",
                              "stock_return",
                              "benchmark_return",
                              "relative_performance",
                              "observations",
                            ].includes(k),
                          )
                          .map(([k, v]) => (
                            <div key={k}>
                              <span>{k}</span>
                              <b>
                                {k.includes("return") ||
                                k === "relative_performance"
                                  ? pct(v)
                                  : num(v)}
                              </b>
                            </div>
                          ))}
                      </div>
                      <p className="muted">
                        {history.benchmark.methodology} Desde{" "}
                        {history.benchmark.start} hasta {history.benchmark.end}{" "}
                        · {history.currency}. Base:{" "}
                        {history.adjusted ? "ajustada" : "SIN AJUSTAR"}.
                      </p>
                    </div>
                  )}
                  <a href={history.source} target="_blank" rel="noreferrer">
                    Metodología del proveedor ↗
                  </a>
                </section>
              ) : (
                <Empty text="No hay serie histórica recuperada. Beta, correlación y comparación sectorial requieren una serie benchmark compatible y no se calculan con datos ausentes." />
              )}
            </>
          )}
          {section === "Stock Screener" && (
            <>
              <form
                className="inline-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  perform("Filtrando", async () =>
                    setScreen(
                      await api(
                        "/screen?" +
                          new URLSearchParams({
                            ...(maxPE ? { max_pe: maxPE } : {}),
                            ...(minYield
                              ? {
                                  min_fcf_yield: String(Number(minYield) / 100),
                                }
                              : {}),
                            ...(minGrowth
                              ? { min_growth: String(Number(minGrowth) / 100) }
                              : {}),
                            ...(maxDebt ? { max_debt_ebitda: maxDebt } : {}),
                            ...(screenIndustry
                              ? { industry: screenIndustry }
                              : {}),
                            sort: screenSort,
                            order: ["symbol", "pe", "debt_ebitda"].includes(
                              screenSort,
                            )
                              ? "asc"
                              : "desc",
                            ...(minMargin
                              ? { min_margin: String(Number(minMargin) / 100) }
                              : {}),
                          }),
                      ),
                    ),
                  );
                }}
              >
                <label>
                  P/E máximo
                  <input
                    type="number"
                    value={maxPE}
                    onChange={(e) => setMaxPE(e.target.value)}
                  />
                </label>
                <label>
                  Margen operativo mínimo (%)
                  <input
                    type="number"
                    value={minMargin}
                    onChange={(e) => setMinMargin(e.target.value)}
                  />
                </label>
                <label>
                  FCF yield mínimo (%)
                  <input
                    type="number"
                    value={minYield}
                    onChange={(e) => setMinYield(e.target.value)}
                  />
                </label>
                <label>
                  Crecimiento ingresos mínimo (%)
                  <input
                    type="number"
                    value={minGrowth}
                    onChange={(e) => setMinGrowth(e.target.value)}
                  />
                </label>
                <label>
                  Deuda / EBITDA máximo
                  <input
                    type="number"
                    value={maxDebt}
                    onChange={(e) => setMaxDebt(e.target.value)}
                  />
                </label>
                <label>
                  Industria
                  <input
                    value={screenIndustry}
                    onChange={(e) => setScreenIndustry(e.target.value)}
                  />
                </label>
                <label>
                  Ordenar por
                  <select
                    value={screenSort}
                    onChange={(e) => setScreenSort(e.target.value)}
                  >
                    <option value="symbol">Ticker</option>
                    <option value="operating_margin">Margen operativo</option>
                    <option value="fcf_yield">FCF yield</option>
                    <option value="revenue_growth">Crecimiento ingresos</option>
                    <option value="pe">P/E</option>
                    <option value="debt_ebitda">Deuda / EBITDA</option>
                  </select>
                </label>
                <button className="primary">Aplicar filtros</button>
              </form>
              {screen && (
                <section className="panel">
                  <Notice>
                    {screen.universe} Universo: {screen.universe_count}{" "}
                    empresas.
                  </Notice>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Empresa</th>
                          <th>Margen EBIT</th>
                          <th>P/E</th>
                          <th>FCF yield</th>
                          <th>Fecha del ejercicio</th>
                        </tr>
                      </thead>
                      <tbody>
                        {screen.rows.map((r: any) => (
                          <tr key={r.symbol}>
                            <td>
                              <button
                                className="text-button"
                                onClick={() => load(r.symbol)}
                              >
                                {r.symbol} <ArrowUpRight size={13} />
                              </button>
                              <small>{r.name}</small>
                            </td>
                            <td>{pct(r.metrics.operating_margin)}</td>
                            <td>{num(r.metrics.pe)}</td>
                            <td>{pct(r.metrics.fcf_yield)}</td>
                            <td>{r.period_end}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!screen.rows.length && (
                    <p className="muted">
                      Ninguna empresa cumple los filtros o todavía no hay datos
                      guardados.
                    </p>
                  )}
                </section>
              )}
            </>
          )}
          {section === "AI Investment Report" && (
            <>
              <div className="report-actions">
                <label>
                  Investigaciones guardadas
                  <select
                    value={job?.id || ""}
                    onChange={(e) =>
                      perform("Abriendo informe", async () =>
                        setJob(await api("/records/" + e.target.value)),
                      )
                    }
                  >
                    <option value="">Seleccionar expediente</option>
                    {saved.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.symbol} · {date(r.created_at)} · {r.data.status}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="secondary"
                  disabled={!job}
                  onClick={exportReport}
                >
                  <ArrowDownToLine size={15} /> JSON auditable
                </button>
                {job && (
                  <a
                    className="secondary"
                    href={"/api/reports/" + job.id + "/pdf"}
                  >
                    Descargar PDF
                  </a>
                )}
                <button
                  className="primary"
                  disabled={!job}
                  onClick={() => window.print()}
                >
                  <FileText size={15} /> Imprimir / guardar PDF
                </button>
              </div>
              {job ? (
                <article className="report panel">
                  <div className="eyebrow">
                    STOCK INTELLIGENCE · RESEARCH DOSSIER
                  </div>
                  <h2>{job.company?.name || job.symbol}</h2>
                  <p>
                    {job.symbol} · {date(job.created_at)} · Estado: {job.status}
                  </p>
                  <HorizonSummary horizon={job.investment_horizon} />
                  <ResearchTimingNotice quality={job.ai?.data?.quality_control} />
                  <Notice>
                    Expediente generado con las fuentes realmente accesibles. No
                    equivale a un informe de equity research completo si faltan
                    datos o síntesis.
                  </Notice>
                  <h3>Resumen de cobertura</h3>
                  <p>
                    {job.report?.summary ||
                      job.error ||
                      "Investigación aún sin resultados."}
                  </p>
                  <h3>Evidencia y análisis original del sistema</h3>
                  {job.ai?.status === "generated_quote_verified" ? (
                    <>
                      <p>{job.ai.data.summary}</p>
                      <ResearchFinancialFacts periods={job.ai.data.financial_facts} withheld={job.ai.data.quality_control?.withheld_financial_count ?? job.ai.data.quality_control?.withheld_count ?? 0} />
                      {job.ai.data.claims.map((c: any, i: number) => (
                        <section className="claim" key={i}>
                          <Badge>{c.kind}</Badge>
                          <p>{c.text}</p>
                          <blockquote>“{c.evidence_quote}”</blockquote>
                          <small>Fuente: {c.source_id}</small>
                          <p>{c.financial_mechanism}</p>
                        </section>
                      ))}
                      {[
                        ["Tesis alcista", "bull_case"],
                        ["Tesis bajista", "bear_case"],
                        ["Contradicciones por revisar", "contradictions"],
                        ["Cuestiones sin resolver", "unresolved"],
                      ].map(([l, k]) => (
                        <section key={k}>
                          <h3>{l}</h3>
                          <ul>
                            {job.ai.data[k].map((t: string, i: number) => (
                              <li key={i}>{t}</li>
                            ))}
                          </ul>
                        </section>
                      ))}
                      <p className="muted">
                        Provider: {job.ai.provider || "openai"} · Model:{" "}
                        {job.ai.model || job.ai.billing?.model}
                      </p>
                      {job.ai.coverage && (
                        <details>
                          <summary>AI evidence coverage and omissions</summary>
                          <pre>{JSON.stringify(job.ai.coverage, null, 2)}</pre>
                        </details>
                      )}
                      {job.ai.limitations?.map(
                        (text: string, index: number) => (
                          <p className="footnote" key={index}>
                            {text}
                          </p>
                        ),
                      )}
                      <pre>{JSON.stringify(job.ai.billing, null, 2)}</pre>
                    </>
                  ) : (
                    <p className="muted">
                      AI synthesis was not generated:{" "}
                      {job.ai?.reason || job.ai?.status || "sin resultados"}. No
                      No conclusions are substituted for missing evidence.
                    </p>
                  )}
                  <ReportSections key={job.id + job.status} id={job.id} />
                  <h3>Fuentes y documentos</h3>
                  {sourceList()}
                  <h3>Valoración y escenarios</h3>
                  <p>
                    Las valoraciones se calculan en Valuation Lab y se conservan
                    por versión. El export JSON incluye las versiones existentes
                    al investigar y las vinculadas después mediante una fuente,
                    identificadas por fecha. Ninguna noticia modifica el modelo
                    por sí sola.
                  </p>
                  {model?.symbol === job.symbol && (
                    <div>
                      <b>
                        Versión guardada abierta: {num(model.fair_value)}{" "}
                        {model.currency} / acción
                      </b>
                      <p className="formula">{model.formula}</p>
                      {projectionChart(model.projections)}
                    </div>
                  )}
                  <h3>Limitaciones y metodología</h3>
                  {job.report?.limitations?.map((l: string) => (
                    <p key={l}>{l}</p>
                  ))}
                  <p>
                    Precio:{" "}
                    {job.market_snapshot
                      ? `${job.market_snapshot.price} ${job.market_snapshot.currency} · ${date(job.market_snapshot.timestamp)} · sin garantía de tiempo real`
                      : "No disponible en esta vista"}
                    . Los datos históricos y las fuentes pueden tener fechas
                    distintas; consulta los registros.
                  </p>
                </article>
              ) : (
                <Empty text="Inicia una investigación o selecciona una guardada para consultar y exportar su expediente." />
              )}
            </>
          )}
          {section === "Watchlist" && (
            <section className="panel">
              <div className="panel-heading">
                <h3>Empresas seguidas</h3>
                <Badge>{watch.length} EMPRESAS</Badge>
              </div>
              {watch.length ? (
                watch.map((w) => (
                  <div className="watch-row" key={w.id}>
                    <button
                      className="ticker-icon"
                      onClick={() => load(w.symbol)}
                    >
                      {w.symbol}
                    </button>
                    <div>
                      <b>{w.symbol}</b>
                      <input
                        aria-label={"Nota para " + w.symbol}
                        defaultValue={w.data.note}
                        placeholder="Tu tesis, un riesgo, una pregunta…"
                        onBlur={(e) => {
                          if (e.target.value !== w.data.note)
                            star(w.symbol, e.target.value);
                        }}
                      />
                    </div>
                    <button
                      className="text-button"
                      onClick={() => load(w.symbol)}
                    >
                      Actualizar ficha <ArrowUpRight size={15} />
                    </button>
                    <button
                      className="icon"
                      aria-label={"Eliminar " + w.symbol}
                      onClick={() =>
                        perform("Eliminando", async () => {
                          await api(
                            "/watchlist/" + w.symbol,
                            undefined,
                            "DELETE",
                          );
                          setWatch(await api("/watchlist"));
                        })
                      }
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              ) : (
                <Empty text="Guarda empresas desde su ficha. La lista y tus notas se conservan en la base de datos." />
              )}
            </section>
          )}
          {section === "Settings" && (
            <>
              <div className="settings-grid">
                {config &&
                  Object.entries(config.providers).map(
                    ([k, v]: [string, any]) => (
                      <section className="panel" key={k}>
                        <div className="panel-heading">
                          <h3>{k.toUpperCase()}</h3>
                          <Badge good={v.configured}>
                            {v.configured
                              ? "Configurado · no verificado"
                              : "Sin configurar"}
                          </Badge>
                        </div>
                        <p>{v.coverage || `Modelo solicitado: ${v.model}`}</p>
                        {k === "local" && (
                          <>
                            <p>
                              Run LM Studio and this application on the same
                              Windows PC. Configuration does not establish
                              connectivity.
                            </p>
                            <p className="muted">
                              Context: {v.context_tokens} tokens ·{" "}
                              {v.enabled
                                ? "Local provider selected"
                                : "Set AI_PROVIDER=local to enable"}
                            </p>
                            <button
                              className="secondary"
                              disabled={!v.enabled || !!busy}
                              onClick={() =>
                                perform("Checking local model", async () => {
                                  setLocalCheck(null);
                                  setLocalCheck(
                                    await api("/settings/local-ai/check", {}),
                                  );
                                })
                              }
                            >
                              Check local model
                            </button>
                            {localCheck && (
                              <p role="status">{localCheck.message}</p>
                            )}
                          </>
                        )}
                        {k === "openai" && !v.enabled && (
                          <p>
                            Paid AI is blocked. Local AI uses a separate
                            configuration and requires no paid-provider key.
                          </p>
                        )}
                        {k === "openai" && v.enabled && (
                          <p>
                            Tarifas:{" "}
                            {v.pricing_configured
                              ? "configuradas"
                              : "pendientes"}
                            . La disponibilidad del modelo se comprueba al
                            solicitarlo.
                          </p>
                        )}
                        <small>
                          La configuración se lee desde variables de entorno del
                          backend. No introduzcas claves en el navegador.
                        </small>
                      </section>
                    ),
                  )}
              </div>
              <section className="panel">
                <h3>Configuración segura</h3>
                <p>
                  Copia .env.example a .env en la raíz del repositorio y
                  configura los proveedores que necesites. Reinicia backend y
                  frontend después de cambiar variables.
                </p>
                <div className="ratio-grid">
                  {config &&
                    Object.entries(config.limits).map(([k, v]) => (
                      <div key={k}>
                        <span>{k}</span>
                        <b>{String(v)}</b>
                      </div>
                    ))}
                </div>
                <p>
                  Persistencia: {config?.storage}. Acceso:{" "}
                  {config?.security.access_token_required
                    ? "token de servidor requerido"
                    : "desarrollo local, sin autenticación de usuarios"}
                  .
                </p>
                <Notice>
                  Antes de exponer la aplicación en internet, añade
                  autenticación de usuarios y HTTPS. APP_TOKEN protege la
                  comunicación interna, no identifica usuarios del frontend.
                </Notice>
                {config?.limitations.map((l: string) => (
                  <p className="muted" key={l}>
                    {l}
                  </p>
                ))}
                <button className="secondary" onClick={refresh}>
                  Actualizar estado
                </button>
              </section>
            </>
          )}
          <footer>
            <span>
              STOCK INTELLIGENCE AI{" "}
              <span className="muted">/ Tu espacio de investigación</span>
            </span>
            <span>
              Fuentes → Cálculos → Hipótesis <ShieldCheck size={13} />
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
