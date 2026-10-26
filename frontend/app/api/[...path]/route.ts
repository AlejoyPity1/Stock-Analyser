import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
const paths =
  /^(health|settings|search|companies|valuation|valuations|research|records|scenarios|scenario-sets|price-scenarios|catalysts|watchlist|screen|compare|relative|relative-analysis|relative-valuations|reports)(\/|$)/;
async function proxy(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const route = path.join("/");
  if (!paths.test(route) || path.some((x) => x === "." || x === ".."))
    return Response.json({ detail: "Ruta no permitida" }, { status: 404 });
  // Requests from another site cannot trigger mutations or paid research.
  if (!["GET", "HEAD"].includes(req.method)) {
    const origin = req.headers.get("origin");
    if (
      origin &&
      origin !== `${req.nextUrl.protocol}//${req.headers.get("host")}`
    )
      return Response.json({ detail: "Origen no permitido" }, { status: 403 });
  }
  const base = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (process.env.APP_TOKEN)
    headers.Authorization = `Bearer ${process.env.APP_TOKEN}`;
  try {
    const body = ["GET", "HEAD"].includes(req.method)
      ? undefined
      : await req.text();
    if (body && body.length > 100000)
      return Response.json(
        { detail: "Solicitud demasiado grande" },
        { status: 413 },
      );
    const result = await fetch(
      `${base}/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`,
      {
        method: req.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(180000),
      },
    );
    return new Response(result.body, {
      status: result.status,
      headers: {
        "Content-Type":
          result.headers.get("Content-Type") || "application/json",
        ...(result.headers.get("Content-Disposition")
          ? {
              "Content-Disposition": result.headers.get("Content-Disposition")!,
            }
          : {}),
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { detail: "Backend no disponible. Inicia FastAPI en el puerto 8000." },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as DELETE };
