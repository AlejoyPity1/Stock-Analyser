"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
export default function ReportSections({ id }: { id: string }) {
  const [report, setReport] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    api("/reports/" + id)
      .then((data) => {
        if (current) setReport(data);
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [id]);
  if (error)
    return (
      <p role="alert">
        No se pudo recuperar la estructura del informe: {error}
      </p>
    );
  if (!report)
    return <p className="muted">Preparando estructura del expediente…</p>;
  if (!report.sections) return null;
  return (
    <div className="report-sections">
      <h3>Informe estructurado · 18 apartados</h3>
      <p className="muted">
        La estructura no implica que todos los apartados estén evaluados. Las
        conclusiones cualitativas esperan la integración de IA local.
      </p>
      {report.sections.map((s: any) => (
        <section className="report-section" key={s.number}>
          <h3>
            {s.number}. {s.title} <span className="badge">{s.status}</span>
          </h3>
          <p>{s.text}</p>
          {s.rows?.length > 0 && (
            <details>
              <summary>Ver datos y evidencia ({s.rows.length})</summary>
              {s.rows.map((r: any, i: number) => (
                <dl key={i}>
                  {Object.entries(r).map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>
                        {v == null
                          ? "No disponible"
                          : typeof v === "object"
                            ? JSON.stringify(v)
                            : String(v)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ))}
            </details>
          )}
        </section>
      ))}
    </div>
  );
}
