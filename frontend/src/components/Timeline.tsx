import type { TimelineTxn } from "../types";
import { clock, day, pkr } from "../utils/format";
import { IndicatorChip } from "./ui";

/** Customer transaction timeline. The anomaly (focus) is highlighted; known device / usual location are shown explicitly. */
export function Timeline({ items }: { items: TimelineTxn[] }) {
  if (!items.length) return <p className="text-sm text-ink-500">No transactions to show.</p>;
  return (
    <ol className="relative ml-2 border-l-2 border-ink-100">
      {items.map((t) => (
        <li key={t.id} className="relative mb-3 ml-5 last:mb-0">
          <span className={`absolute -left-[28px] top-3 h-3.5 w-3.5 rounded-full border-2 border-white ${t.is_anomaly ? "bg-red-600 animate-pulseRing" : "bg-ink-300"}`} />
          <div className={`rounded-lg border px-3 py-2 ${t.is_focus ? "border-red-300 bg-red-50" : t.is_anomaly ? "border-orange-200 bg-orange-50/60" : "border-ink-100 bg-white"}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-medium text-ink-500">{day(t.occurred_at)} · {clock(t.occurred_at)}</span>
              <span className={`text-sm font-semibold tabular-nums ${t.is_anomaly ? "text-red-700" : "text-ink-900"}`}>{pkr(t.amount)}</span>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-600">
              <span>{t.merchant}</span>
              <span className={t.usual_location ? "" : "font-semibold text-red-700"}>{t.location}{t.usual_location ? "" : " · Unusual Location"}</span>
              <span className={t.known_device ? "" : "font-semibold text-red-700"}>{t.known_device ? "Known Device" : "New Device"}</span>
              {t.is_focus && <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white">ANOMALY</span>}
            </div>
            {t.indicator_codes.length > 0 && <div className="mt-1.5 flex flex-wrap gap-1">{t.indicator_codes.map((c) => <IndicatorChip key={c} code={c} />)}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}
