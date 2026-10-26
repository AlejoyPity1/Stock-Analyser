import { test, expect } from "@playwright/test";

test("home shows empty evidence state and backend configuration", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Una acción." }),
  ).toBeVisible();
  await expect(
    page.getByText("Aún no has consultado ninguna empresa.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Configuración", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Configuración segura" }),
  ).toBeVisible();
  await expect(page.getByText("Sin configurar", { exact: true })).toHaveCount(
    5,
  );
  expect(errors).toEqual([]);
});

test("manual DCF is calculated by real backend, including sensitivity", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Valoración DCF", exact: true })
    .click();
  const values: Record<string, string> = {
    "Ingresos base (millones)": "1000",
    "Crecimiento anual (%)": "0",
    "Margen operativo (%)": "20",
    "Tipo impositivo (%)": "0",
    "Capex / ingresos (%)": "0",
    "D&A / ingresos (%)": "0",
    "NWC / ingresos (%)": "0",
    "WACC nominal (%)": "10",
    "Crecimiento terminal (%)": "0",
    "Deuda neta (millones)": "0",
    "Acciones diluidas (millones)": "100",
    "Precio opcional / acción": "10",
  };
  for (const [label, value] of Object.entries(values))
    await page.getByLabel(label, { exact: true }).fill(value);
  await page.getByRole("button", { name: "Calcular DCF", exact: true }).click();
  await expect(page.locator(".fair-value")).toContainText("20");
  await expect(
    page.locator(".result-line").filter({ hasText: "Upside / downside" }),
  ).toContainText("100%");
  await expect(
    page.getByRole("heading", { name: "Sensibilidad WACC / g terminal" }),
  ).toBeVisible();
  await page.getByLabel("WACC nominal (%)", { exact: true }).fill("2");
  await page.getByLabel("Crecimiento terminal (%)", { exact: true }).fill("2");
  await page.getByRole("button", { name: "Calcular DCF", exact: true }).click();
  await expect(page.locator(".error-banner")).toContainText(
    "WACC debe superar",
  );
});

test("missing provider fails visibly without invented company data", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "AAPL", exact: true }).click();
  await expect(page.locator(".error-banner")).toContainText("SEC_USER_AGENT");
  await expect(page.locator(".company-chip")).toHaveCount(0);
});

test("watchlist is persisted through actual API and removed", async ({
  page,
  request,
}) => {
  await request.post("/api/watchlist", {
    data: {
      symbol: "TEST",
      note: "Controlled browser test; not financial data",
    },
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Seguimiento", exact: false })
    .first()
    .click();
  await expect(page.getByLabel("Nota para TEST")).toHaveValue(
    "Controlled browser test; not financial data",
  );
  await page.getByLabel("Eliminar TEST").click();
  await expect(page.getByLabel("Nota para TEST")).toHaveCount(0);
});

test("mobile navigation and desktop have no horizontal overflow", async ({
  page,
}) => {
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "/tmp/stock-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByLabel("Abrir navegación").click();
  await page
    .getByRole("button", { name: "Valoración DCF", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Hipótesis del modelo" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "/tmp/stock-mobile.png", fullPage: true });
});

test("controlled research dossier renders sources and exports JSON and printable PDF", async ({
  page,
}) => {
  // Rendering/export fixture only; this is never live financial data.
  const fixture = {
    id: "controlled-report",
    symbol: "TEST",
    status: "completed",
    stage: "Controlled fixture",
    created_at: "2024-01-01T12:00:00Z",
    updated_at: "2024-01-01T12:01:00Z",
    request: { mode: "quick" },
    company: { name: "CONTROLLED TEST FIXTURE" },
    sources: [
      {
        id: "fixture-source",
        title: "Synthetic document for export test",
        publisher: "Controlled test",
        url: "https://example.org/test-document",
        published_at: "2024-01-01",
        retrieved_at: "2024-01-01T12:00:00Z",
        read_status: "abstract_only",
        full_text: false,
        summary:
          "Synthetic content used only inside an automated browser test.",
      },
    ],
    ai: { status: "not_requested" },
    report: {
      summary: "Controlled export test; no real company analysis.",
      limitations: ["Test fixture only."],
    },
  };
  await page.route("**/api/records?kind=research", (route) =>
    route.fulfill({
      json: [
        {
          id: fixture.id,
          symbol: "TEST",
          created_at: fixture.created_at,
          data: fixture,
        },
      ],
    }),
  );
  await page.route("**/api/records/controlled-report", (route) =>
    route.fulfill({ json: fixture }),
  );
  await page.route("**/api/reports/controlled-report", (route) =>
    route.fulfill({ json: { record: fixture } }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Informes", exact: true }).click();
  await page.getByLabel("Investigaciones guardadas").selectOption(fixture.id);
  await expect(
    page.getByRole("heading", { name: "CONTROLLED TEST FIXTURE" }),
  ).toBeVisible();
  await expect(
    page.getByText("Horizonte no registrado en este expediente.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.getByText("Solo extracto", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Synthetic document for export test" }),
  ).toHaveAttribute("href", "https://example.org/test-document");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "JSON auditable" }).click();
  expect((await download).suggestedFilename()).toBe("informe-TEST.json");
  await page.getByRole("button", { name: "Inicio", exact: true }).click();
  await page.locator(".report-shortcut").filter({ hasText: "TEST" }).click();
  await expect(page.getByLabel("Investigaciones guardadas")).toHaveValue(
    fixture.id,
  );
  await expect(page.locator(".company-chip")).toContainText("TEST");
  const pdf = await page.pdf({ format: "A4", printBackground: true });
  expect(pdf.subarray(0, 4).toString()).toBe("%PDF");
  expect(pdf.length).toBeGreaterThan(5000);
});

test("research report shows period-labelled unscaled financial facts and withheld-statement notice", async ({ page }) => {
  const fact = (value: number, unit: string) => ({ value, unit, source: "https://www.sec.gov/Archives/controlled", filed: "2026-05-01", quality: "reported" });
  const fixture = {
    id: "controlled-grounded-report", symbol: "TEST", status: "completed", created_at: "2026-10-26T12:00:00Z",
    request: { mode: "quick" }, company: { name: "CONTROLLED GROUNDED FIXTURE" }, sources: [],
    report: { summary: "Controlled financial display fixture.", limitations: [] },
    ai: { status: "generated_quote_verified", provider: "local", model: "controlled-test",
      data: { summary: "Controlled extraction test.", claims: [], bull_case: [], bear_case: [], contradictions: [], unresolved: [],
        quality_control: { withheld_count: 1 },
        financial_facts: [{ period_type: "quarter", period_start: "2025-12-28", period_end: "2026-03-28", values: {
          net_income: fact(29578000000, "USD"), eps: fact(2.01, "USD/shares"), shares: fact(14725873000, "shares"),
        }}],
      }, billing: { estimated_cost_usd: 0 } },
  };
  await page.route("**/api/records?kind=research", route => route.fulfill({ json: [{ id: fixture.id, symbol: fixture.symbol, created_at: fixture.created_at, data: fixture }] }));
  await page.route("**/api/records/controlled-grounded-report", route => route.fulfill({ json: fixture }));
  await page.route("**/api/reports/controlled-grounded-report", route => route.fulfill({ json: { record: fixture } }));
  await page.goto("/");
  await page.getByRole("button", { name: "Informes", exact: true }).click();
  await page.getByLabel("Investigaciones guardadas").selectOption(fixture.id);
  const financial = page.getByRole("region", { name: "Reported financial context" });
  await expect(financial).toContainText("2025-12-28 to 2026-03-28");
  await expect(financial).toContainText("29,578,000,000");
  await expect(financial).toContainText("14,725,873,000");
  await expect(financial).toContainText("USD/shares");
  await expect(financial).toContainText("1 numerical financial statement(s) from the AI were withheld");
  await page.setViewportSize({ width: 320, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test("search supports keyboard selection, arbitrary tickers and visible provider errors", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/search?q=*", (route) =>
    route.fulfill({
      json: [
        {
          symbol: "CUSTOM.A",
          name: "Controlled first result",
          exchange: "TEST",
        },
        {
          symbol: "CUSTOM.B",
          name: "Controlled second result",
          exchange: "TEST",
        },
      ],
    }),
  );
  await page.route("**/api/companies/CUSTOM.B", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Proveedor no disponible para CUSTOM.B" },
    }),
  );
  await page.goto("/");
  await page.keyboard.press("Control+k");
  await expect(page.getByLabel("Buscar empresa o ticker")).toBeFocused();
  await page.getByLabel("Buscar empresa o ticker").fill("custom");
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: /CUSTOM.A/ })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(dialog.getByRole("button", { name: /CUSTOM.B/ })).toBeFocused();
  const request = page.waitForRequest((request) =>
    request.url().endsWith("/api/companies/CUSTOM.B"),
  );
  await page.keyboard.press("Enter");
  await request;
  await expect(dialog.getByRole("alert")).toContainText(
    "Proveedor no disponible para CUSTOM.B",
  );
  await page.setViewportSize({ width: 360, height: 780 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Buscar empresa o ticker")).toBeFocused();
  await expect(page.locator(".company-chip")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("home horizon selection follows the user into research and back", async ({
  page,
}) => {
  await page.goto("/");
  const horizon = page.getByRole("group", {
    name: "Horizonte de la próxima investigación",
  });
  await expect(
    horizon.getByRole("button", { name: "3–6 meses", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await horizon.getByRole("button", { name: "6 meses", exact: true }).click();
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  await expect(
    page.getByLabel("Horizonte de inversión", { exact: true }),
  ).toHaveValue("6m");
  await page
    .getByLabel("Horizonte de inversión", { exact: true })
    .selectOption("3m");
  await page.getByRole("button", { name: "Inicio", exact: true }).click();
  await expect(
    horizon.getByRole("button", { name: "3 meses", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("local AI is enabled independently of paid AI and checks connectivity without claiming generation", async ({
  page,
}) => {
  await page.route("**/api/settings", async (route) => {
    const response = await route.fetch();
    const settings = await response.json();
    settings.ai_provider = "local";
    settings.providers.local.enabled = true;
    settings.providers.local.configured = true;
    settings.providers.openai.enabled = false;
    await route.fulfill({ json: settings });
  });
  await page.route("**/api/settings/local-ai/check", (route) =>
    route.fulfill({
      json: {
        status: "reachable",
        model: "qwen/qwen3.5-9b",
        inference_verified: false,
        message:
          "Model ID is listed. This check does not test generation, GPU use or financial accuracy.",
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  const toggle = page.getByLabel("Use AI for evidence analysis", {
    exact: true,
  });
  await expect(toggle).toBeEnabled();
  await expect(toggle).toBeChecked();
  await expect(
    page.getByText("Local · qwen/qwen3.5-9b", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Presupuesto máximo USD", { exact: false }),
  ).toHaveCount(0);
  await toggle.uncheck();
  await page
    .getByRole("button", { name: "Configuración", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Check local model", exact: true })
    .click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "This check does not test generation" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  await expect(toggle).not.toBeChecked();
});

test("mobile drawer traps focus, closes with Escape and restores navigation", async ({
  page,
}) => {
  await page.setViewportSize({ width: 720, height: 900 });
  await page.goto("/");
  await page.getByLabel("Abrir navegación").click();
  await expect(
    page.getByLabel("Cerrar navegación", { exact: true }),
  ).toBeFocused();
  await expect(page.locator("main")).toHaveAttribute("inert", "");
  await page
    .getByRole("button", { name: "Configuración", exact: true })
    .focus();
  await page.keyboard.press("Tab");
  await expect(page.locator(".brand")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.locator("main")).not.toHaveAttribute("inert", "");
  await expect(page.getByLabel("Abrir navegación")).toBeFocused();
  await page.setViewportSize({ width: 320, height: 740 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByLabel("Abrir navegación").click();
  await page
    .getByRole("button", { name: "Valoración DCF", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Hipótesis del modelo" }),
  ).toBeVisible();
  await expect(page.locator(".nav-backdrop")).toHaveCount(0);
});

test("relative valuation shows peer eligibility, audit history and dirty inputs", async ({
  page,
}) => {
  const base = {
    symbol: "TARGET",
    status: "available",
    created_at: "2026-01-01T12:00:00Z",
    inputs: {
      target: "TARGET",
      peers: ["PEERA", "PEERB"],
      metric: "pe",
      basis: "annual",
      rationale:
        "Controlled test group with synthetic data, only for interface verification.",
    },
    target: { symbol: "TARGET", reasons: [], snapshot: {} },
    peers: [
      {
        symbol: "PEERA",
        name: "Controlled A",
        eligible: true,
        reasons: [],
        currency: "USD",
        period_end: "2025-12-31",
        multiple: 10,
        operating_margin: 0.2,
      },
      {
        symbol: "PEERB",
        name: "Controlled B",
        eligible: true,
        reasons: [],
        currency: "USD",
        period_end: "2025-12-31",
        multiple: 20,
        operating_margin: 0.3,
      },
    ],
    selected_count: 2,
    accepted_count: 2,
    distribution: { median: 15, min: 10, max: 20 },
    implied_per_share: 15,
    currency: "USD",
    upside: -0.25,
    market_multiple_gap: 1 / 3,
    formula: "Controlled test formula",
    sensitivity: [
      { multiple: 10, implied_per_share: 10 },
      { multiple: 15, implied_per_share: 15 },
      { multiple: 20, implied_per_share: 20 },
    ],
    limitations: ["Controlled fixture; no real financial claims."],
  };
  let saved: any[] = [];
  await page.route("**/api/records?kind=relative&symbol=TARGET", (route) =>
    route.fulfill({ json: saved }),
  );
  await page.route("**/api/relative-analysis", (route) =>
    route.fulfill({ json: base }),
  );
  await page.route("**/api/relative-valuations", (route) => {
    const data = { ...base, id: "controlled-relative" };
    saved = [{ id: data.id, created_at: data.created_at, data }];
    return route.fulfill({ json: data });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Comparables", exact: true }).click();
  await page
    .getByLabel("Empresa objetivo de comparables", { exact: true })
    .fill("TARGET");
  await page
    .getByLabel("Pares de valoración", { exact: true })
    .fill("PEERA,PEERB");
  await page
    .getByLabel("Justificación de comparabilidad", { exact: true })
    .fill(base.inputs.rationale);
  await page
    .getByRole("button", { name: "Calcular comparables", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Valor implícito condicional",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("Admitido", { exact: true })).toHaveCount(2);
  await page
    .getByRole("button", { name: "Guardar valoración relativa", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Valoraciones relativas guardadas" }),
  ).toBeVisible();
  await page
    .getByLabel("Múltiplo de valoración relativa", { exact: true })
    .selectOption("ev_ebitda");
  await expect(
    page.getByText("Hay cambios sin recalcular.", { exact: false }),
  ).toBeVisible();
});

test("catalyst register persists evidence and immutable cancellation revision", async ({
  page,
}) => {
  const symbol = "CAT" + Date.now().toString().slice(-6);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  const board = page.locator("section.panel").filter({
    has: page.getByRole("heading", {
      name: "Registro de catalizadores",
      exact: true,
    }),
  });
  await board
    .getByLabel("Empresa del catalizador", { exact: true })
    .fill(symbol);
  await board
    .getByText("Registrar catalizador y evidencia", { exact: true })
    .click();
  await board
    .getByLabel("Título del catalizador", { exact: true })
    .fill("CONTROLLED TEST: quarterly catalyst");
  await board
    .getByLabel("Fecha del evento", { exact: true })
    .fill("2026-12-15");
  await board
    .getByLabel("Enlace de la fuente", { exact: true })
    .fill("https://example.org/controlled-catalyst");
  await board
    .getByLabel("Hipótesis de impacto", { exact: true })
    .fill(
      "CONTROLLED TEST: validate manual evidence persistence, not a real event.",
    );
  await board
    .getByLabel("Invalidación del catalizador", { exact: true })
    .fill("Controlled event is cancelled or rescheduled.");
  await board
    .getByRole("button", { name: "Guardar catalizador", exact: true })
    .click();
  await expect(board.getByRole("status")).toContainText("Catalizador guardado");
  await expect(board.locator(".source-card")).toHaveCount(1);
  await expect(
    board.getByText("Referencia externa sin verificación del texto", {
      exact: false,
    }),
  ).toBeVisible();
  await board
    .getByRole("button", { name: "Editar en una nueva versión", exact: true })
    .click();
  await board
    .getByLabel("Estado del evento", { exact: true })
    .selectOption("cancelled");
  await board
    .getByRole("button", {
      name: "Guardar nueva versión del catalizador",
      exact: true,
    })
    .click();
  await expect(board.locator(".source-card")).toHaveCount(1);
  await expect(board.locator(".source-card")).toContainText("cancelled");
  await board
    .getByRole("button", { name: "Editar en una nueva versión", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("price scenario UI preserves manual assumptions, audit export and dirty-input warning", async ({
  page,
}) => {
  // UI fixture only. Numerical calculation and live-provider paths have separate tests.
  let saved = false;
  const model: any = {
    symbol: "CUSTOM",
    currency: "USD",
    model_version: "price-horizon-1.0",
    created_at: "2026-10-26T12:00:00Z",
    catalysts: [],
    reference_quote: { price: 100, timestamp: "2026-10-23T20:00:00Z" },
    investment_horizon: {
      code: "3m",
      label: "3 meses",
      as_of: "2026-10-26",
      window_start_date: "2027-01-26",
      window_end_date: "2027-01-26",
      interpretation: "Controlled research context, not a price forecast.",
      focus: [],
    },
    limitations: ["Controlled UI fixture only."],
    horizons: {
      "3": {
        target_date: "2027-01-26",
        conditional_reward_risk: 1.105263,
        reward_risk_interpretation: "Conditional cases; no probabilities.",
        cases: {
          bear: {
            price: 80,
            price_return: -0.2,
            gross_return_with_dividends: -0.19,
            breakeven_pe: 24.75,
          },
          base: {
            price: 100,
            price_return: 0,
            gross_return_with_dividends: 0.01,
            breakeven_pe: 19.8,
          },
          bull: {
            price: 120,
            price_return: 0.2,
            gross_return_with_dividends: 0.21,
            breakeven_pe: 16.5,
          },
        },
      },
    },
  };
  await page.route("**/api/price-scenarios**", async (route) => {
    model.inputs = route.request().postDataJSON();
    if (!route.request().url().endsWith("/preview")) {
      model.id = "controlled-price-model";
      saved = true;
    }
    await route.fulfill({ json: model });
  });
  await page.route(
    "**/api/records?kind=price_scenario&symbol=CUSTOM",
    (route) =>
      route.fulfill({
        json: saved
          ? [
              {
                id: model.id,
                symbol: "CUSTOM",
                created_at: model.created_at,
                data: model,
              },
            ]
          : [],
      }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Escenarios de precio", exact: true })
    .click();
  await page
    .getByLabel("Empresa de escenarios", { exact: true })
    .fill("CUSTOM");
  await page
    .getByLabel("Divisa de escenarios de cotización", { exact: true })
    .fill("USD");
  await page
    .getByLabel("Horizonte de escenarios de cotización", { exact: true })
    .selectOption("3m");
  for (const [name, eps] of [
    ["Bajista", "4"],
    ["Base", "5"],
    ["Alcista", "6"],
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await page.getByLabel("EPS forward 12 meses", { exact: true }).fill(eps);
    await page.getByLabel("P/E supuesto", { exact: true }).fill("20");
    await page
      .getByLabel("Dividendos por acción del horizonte", { exact: true })
      .fill("1");
    await page
      .getByLabel("Fundamento del escenario de cotización", { exact: true })
      .fill(
        "CONTROLLED TEST: explicit manual assumptions, not real forecasts.",
      );
    await page
      .getByLabel("Invalidación del escenario de cotización", { exact: true })
      .fill("Controlled future earnings assumption is no longer supported.");
  }
  await page
    .getByRole("button", {
      name: "Calcular escenarios de cotización",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("cell", { name: "100 USD", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Guardar escenarios de cotización",
      exact: true,
    })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Escenarios de cotización guardados",
  );
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Exportar escenarios JSON", exact: true })
    .click();
  expect((await download).suggestedFilename()).toBe("escenarios-CUSTOM.json");
  await page.getByLabel("P/E supuesto", { exact: true }).fill("22");
  await expect(
    page.getByText("Hay cambios sin recalcular.", { exact: false }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
