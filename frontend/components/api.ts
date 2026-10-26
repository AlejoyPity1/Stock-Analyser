export async function api<T = any>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method: method || (body ? "POST" : "GET"),
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json();
  if (!r.ok)
    throw new Error(
      typeof d.detail === "string"
        ? d.detail
        : Array.isArray(d.detail)
          ? d.detail
              .map(
                (e: any) =>
                  `${e.loc?.slice(1).join(" / ") || "Modelo"}: ${e.msg}`,
              )
              .join("; ")
          : JSON.stringify(d.detail || d),
    );
  return d;
}
export const num = (n: unknown, d = 2) =>
  typeof n === "number"
    ? new Intl.NumberFormat("es-ES", { maximumFractionDigits: d }).format(n)
    : "—";
export const compact = (n: unknown) =>
  typeof n === "number"
    ? new Intl.NumberFormat("es-ES", {
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(n)
    : "—";
export const pct = (n: unknown) =>
  typeof n === "number" ? num(n * 100) + "%" : "—";
export const date = (n: string | undefined) =>
  n ? new Date(n).toLocaleString("es-ES") : "—";
export function download(name: string, data: unknown) {
  const u = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = u;
  a.download = name;
  a.click();
  URL.revokeObjectURL(u);
}
