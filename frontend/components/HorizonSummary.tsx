"use client";

export default function HorizonSummary({ horizon }: { horizon?: any }) {
  if (!horizon) {
    return (
      <p className="muted">
        Horizonte no registrado en este expediente. Los informes anteriores
        conservan su contexto original.
      </p>
    );
  }
  return (
    <div className="notice">
      <div>
        <strong>Horizonte del análisis: {horizon.label}</strong>
        <p>
          Fecha base: {horizon.as_of} · Ventana: {horizon.window_start_date} a{" "}
          {horizon.window_end_date}.
        </p>
        <p>{horizon.interpretation}</p>
        <details>
          <summary>Enfoque de investigación</summary>
          <ul>
            {horizon.focus.map((focus: string) => (
              <li key={focus}>{focus}</li>
            ))}
          </ul>
          <p>
            Estos puntos guían la investigación; su presencia no significa que
            estén evaluados.
          </p>
        </details>
      </div>
    </div>
  );
}
