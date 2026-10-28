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
        <strong>Investment horizon: {horizon.label}</strong>
        <p>
          Analysis period: {horizon.as_of} to{" "}
          {horizon.window_end_date}.
        </p>
        <p>
          {horizon.window_start_date === horizon.window_end_date
            ? `Target date: ${horizon.window_end_date}.`
            : `Target dates: ${horizon.window_start_date} to ${horizon.window_end_date}.`}
          {" "}Events before the target dates can affect the outcome.
        </p>
        <p>{horizon.interpretation}</p>
        <details>
          <summary>Research focus</summary>
          <ul>
            {(horizon.focus || []).map((focus: string) => (
              <li key={focus}>{focus}</li>
            ))}
          </ul>
          <p>
            These points guide the research; their presence does not mean they
            have been evaluated.
          </p>
        </details>
      </div>
    </div>
  );
}
