"use client";

export default function ResearchTimingNotice({ quality }: { quality?: any }) {
  const count = quality?.withheld_horizon_count || 0;
  if (!count) return null;
  const periods = Array.from(
    new Map<string, any>(
      (quality.withheld || [])
        .filter((item: any) => item.category === "horizon_inclusion")
        .map((item: any) => [
          `${item.source_period_start}/${item.source_period_end}/${item.analysis_end}`,
          item,
        ]),
    ).values(),
  );
  return (
    <div className="notice" role="note" aria-label="Event timing review">
      <div>
        <strong>Event timing needs review</strong>
        <p>
          {count} timing claim(s) were withheld because the cited period does not
          establish an event date within your analysis period.
        </p>
        {periods.slice(0, 4).map((period: any) => (
          <p key={`${period.source_period_start}/${period.source_period_end}`}>
            Source period: {period.source_period_start} to {period.source_period_end}.
            {" "}Analysis period: {period.analysis_start} to {period.analysis_end}.
          </p>
        ))}
        <p>An expected period is not a confirmed catalyst date.</p>
      </div>
    </div>
  );
}
