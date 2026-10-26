import { test, expect } from "@playwright/test";
// Explicit opt-in integration: actual SEC/Finnhub data, never AI calls.
test.skip(
  process.env.RUN_LIVE !== "1",
  "Live providers require credentials and explicit opt-in",
);
test("real company → statements/TTM → saved DCF/scenarios → research → PDF", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const settings = await (await request.get("/api/settings")).json();
  expect(settings.providers.openai.enabled).toBe(false);
  await page.goto("/");
  await page.getByRole("button", { name: "AAPL", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Apple Inc.", exact: true }),
  ).toBeVisible({ timeout: 45000 });
  const company = await (await request.get("/api/companies/AAPL")).json();
  expect(company.company.currency).toBe("USD");
  expect(company.quote.currency).toBe("USD");
  await page.setViewportSize({ width: 320, height: 850 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("button", { name: "Estados financieros", exact: true })
    .click();
  await page.getByLabel("Base del estado", { exact: true }).selectOption("ttm");
  await expect(
    page.getByRole("columnheader", { name: company.company.ttm.end }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Valoración DCF", exact: true })
    .click();
  await page.getByRole("button", { name: "Usar último ejercicio" }).click();
  await expect(
    page.getByLabel("Ingresos base (millones)", { exact: true }),
  ).toHaveValue(
    String(company.company.statements[0].values.revenue.value / 1e6),
  );
  await page
    .getByLabel("Fundamento de los supuestos", { exact: true })
    .fill(
      "VALIDACIÓN AUTOMATIZADA con fundamentales reales y supuestos de prueba; no son previsiones ni recomendación.",
    );
  await page.getByRole("button", { name: "Calcular DCF", exact: true }).click();
  await expect(page.locator(".fair-value")).toBeVisible();
  await page
    .getByRole("button", { name: "Guardar versión", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Versiones guardadas" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Escenarios de precio", exact: true })
    .click();
  await page.getByRole("button", { name: "Copiar hipótesis del DCF" }).click();
  await page
    .getByRole("button", { name: "Guardar escenarios", exact: true })
    .click();
  await expect(
    page.getByText("Escenarios guardados ·", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Precio y riesgo", exact: true })
    .click();
  await page
    .getByLabel("Benchmark opcional (ticker US)", { exact: true })
    .fill("SPY");
  await page
    .getByRole("button", { name: "Recuperar histórico", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Comparación con SPY" }),
  ).toBeVisible({ timeout: 45000 });
  await expect(
    page.getByText("PRECIOS SIN AJUSTAR.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Comparables", exact: true }).click();
  await page
    .getByLabel("De 2 a 5 tickers, separados por coma")
    .fill("AAPL,GPRK,ASML");
  await page.getByRole("button", { name: "Comparar", exact: true }).click();
  await expect(
    page.getByText("Divisas distintas: múltiplos no calculados", {
      exact: true,
    }),
  ).toBeVisible({ timeout: 45000 });
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  await expect(
    page.getByLabel("Horizonte de inversión", { exact: true }),
  ).toHaveValue("3-6m");
  await expect(page.getByLabel("Use AI for evidence analysis")).toBeDisabled();
  await page
    .getByRole("button", { name: "Investigación rápida", exact: true })
    .click();
  await expect(
    page.getByText("Recopilación terminada", { exact: true }),
  ).toBeVisible({ timeout: 90000 });
  await expect(
    page.getByText("Horizonte del análisis: 3–6 meses", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Documento leído", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Informes", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Informe estructurado · 18 apartados" }),
  ).toBeVisible();
  const href = await page
    .getByRole("link", { name: "Descargar PDF", exact: true })
    .getAttribute("href");
  const report = await (await request.get(href!.replace(/\/pdf$/, ""))).json();
  expect(report.investment_horizon.code).toBe("3-6m");
  expect(report.investment_horizon.as_of).toBe(
    report.record.created_at.slice(0, 10),
  );
  const pdf = await request.get(href!);
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");
  await page.screenshot({ path: "/tmp/stock-live-report.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("real relative valuation preserves actual selected peer inputs", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  page.setDefaultTimeout(15000);
  await page.goto("/");
  await page.getByRole("button", { name: "Comparables", exact: true }).click();
  await page
    .getByLabel("Empresa objetivo de comparables", { exact: true })
    .fill("MSFT");
  await page
    .getByLabel("Pares de valoración", { exact: true })
    .fill("ADP,INTU");
  await page
    .getByLabel("Justificación de comparabilidad", { exact: true })
    .fill(
      "VALIDACIÓN AUTOMATIZADA: software y servicios empresariales USD con cierres próximos; las diferencias de negocio, márgenes y riesgo requieren revisión y no certifican comparabilidad económica.",
    );
  await page
    .getByRole("button", { name: "Calcular comparables", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Valor implícito condicional",
      exact: true,
    }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("Admitido", { exact: true })).toHaveCount(2);
  const savedResponse = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/relative-valuations") &&
      r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Guardar valoración relativa", exact: true })
    .click();
  const response = await savedResponse;
  expect(response.status()).toBe(200);
  const saved = await response.json();
  expect(saved.inputs.target).toBe("MSFT");
  expect(saved.accepted_count).toBe(2);
  expect(saved.target.snapshot.period.values.net_income.value).toBeGreaterThan(
    0,
  );
  expect(saved.target.snapshot.quote.currency).toBe("USD");
  expect(saved.distribution.median).toBeCloseTo(
    (saved.peers[0].multiple + saved.peers[1].multiple) / 2,
    8,
  );
  const restored = await (await request.get("/api/records/" + saved.id)).json();
  expect(restored.implied_per_share).toBe(saved.implied_per_share);
  await expect(
    page.getByRole("heading", { name: "Valoraciones relativas guardadas" }),
  ).toBeVisible();
  await page.screenshot({
    path: "/tmp/stock-relative-live.png",
    fullPage: true,
  });
});

test("typed ticker and chosen three-month horizon reach the saved research report", async ({
  page,
  request,
}) => {
  test.setTimeout(150000);
  await page.goto("/");
  await page.getByLabel("Ticker para investigar", { exact: true }).fill("NVDA");
  await page
    .getByRole("button", { name: "Buscar acción", exact: true })
    .click();
  await page
    .locator(".search-match")
    .filter({ hasText: "NVDA" })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: /NVIDIA/i }).first(),
  ).toBeVisible({ timeout: 45000 });
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  await page
    .getByLabel("Horizonte de inversión", { exact: true })
    .selectOption("3m");
  const createdResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/research") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Investigación rápida", exact: true })
    .click();
  const created = await (await createdResponse).json();
  expect(created.symbol).toBe("NVDA");
  expect(created.investment_horizon.code).toBe("3m");
  await expect(
    page.getByText("Recopilación terminada", { exact: true }),
  ).toBeVisible({ timeout: 90000 });
  await expect(
    page.getByText("Horizonte del análisis: 3 meses", { exact: true }),
  ).toBeVisible();
  const report = await (await request.get("/api/reports/" + created.id)).json();
  expect(report.record.symbol).toBe("NVDA");
  expect(report.investment_horizon).toEqual(created.investment_horizon);
  expect(report.investment_horizon.window_start_date).toBe(
    report.investment_horizon.window_end_date,
  );
  await page
    .getByRole("button", { name: "Escenarios de precio", exact: true })
    .click();
  await page
    .getByLabel("Horizonte de escenarios de cotización", { exact: true })
    .selectOption("3m");
  for (const [name, pe] of [
    ["Bajista", "10"],
    ["Base", "20"],
    ["Alcista", "30"],
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await page.getByLabel("EPS forward 12 meses", { exact: true }).fill("1");
    await page.getByLabel("P/E supuesto", { exact: true }).fill(pe);
    await page
      .getByLabel("Dividendos por acción del horizonte", { exact: true })
      .fill("0");
    await page
      .getByLabel("Fundamento del escenario de cotización", { exact: true })
      .fill(
        "VALIDACIÓN AUTOMATIZADA: EPS y P/E hipotéticos para probar el motor; no son previsiones ni recomendación.",
      );
    await page
      .getByLabel("Invalidación del escenario de cotización", { exact: true })
      .fill(
        "VALIDACIÓN: la hipótesis de beneficio deja de estar respaldada por evidencia.",
      );
  }
  const modelResponse = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/price-scenarios") &&
      r.request().method() === "POST",
  );
  await page
    .getByRole("button", {
      name: "Guardar escenarios de cotización",
      exact: true,
    })
    .click();
  const modelSaved = await modelResponse;
  expect(modelSaved.status()).toBe(200);
  const model = await modelSaved.json();
  expect(model.symbol).toBe("NVDA");
  expect(model.reference_quote.price).toBeGreaterThan(0);
  expect(model.horizons["3"].cases.base.price).toBe(20);
  const complete = await (
    await request.get("/api/reports/" + created.id)
  ).json();
  expect(complete.price_scenarios.some((s: any) => s.id === model.id)).toBe(
    true,
  );
  const pdf = await request.get("/api/reports/" + created.id + "/pdf");
  expect(pdf.status()).toBe(200);
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");
  await page
    .getByRole("button", { name: "Investigación", exact: true })
    .click();
  const calendarResponse = page.waitForResponse((r) =>
    r.url().endsWith("/api/companies/NVDA/earnings-calendar"),
  );
  await page
    .getByRole("button", {
      name: "Consultar calendario de resultados",
      exact: true,
    })
    .click();
  const calendar = await calendarResponse;
  expect(calendar.status()).toBe(200);
  const calendarData = await calendar.json();
  expect(calendarData.symbol).toBe("NVDA");
  expect(
    calendarData.items.every((item: any) => item.date_status === "estimated"),
  ).toBe(true);
  await page.screenshot({
    path: "/tmp/stock-horizon-nvda.png",
    fullPage: true,
  });
});
