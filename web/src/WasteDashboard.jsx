/**
 * The signature visual: shows how well the generated plan uses up the pantry.
 * This is what makes MealMind memorable — it quantifies food-waste avoided.
 */
export default function WasteDashboard({ report }) {
  if (!report) return null;

  const util = report.pantry_utilization_pct;
  const rescued = report.expiring_soon_used;
  const atRisk = report.expiring_soon_total;

  return (
    <div className="card dashboard">
      <h3>♻️ Waste report</h3>
      <div className="gauges">
        <Gauge
          label="Pantry used"
          value={`${util}%`}
          sub={`${report.pantry_items_used}/${report.pantry_items_total} items`}
          tone={util >= 70 ? "good" : util >= 40 ? "ok" : "warn"}
        />
        <Gauge
          label="Expiring items rescued"
          value={atRisk ? `${rescued}/${atRisk}` : "—"}
          sub={atRisk ? "before they spoil" : "none expiring soon"}
          tone={atRisk === 0 || rescued === atRisk ? "good" : "warn"}
        />
      </div>

      {report.unused_items.length > 0 && (
        <p className="unused">
          Still unused: {report.unused_items.join(", ")}
        </p>
      )}
    </div>
  );
}

function Gauge({ label, value, sub, tone }) {
  return (
    <div className={`gauge ${tone}`}>
      <div className="gauge-value">{value}</div>
      <div className="gauge-label">{label}</div>
      <div className="gauge-sub">{sub}</div>
    </div>
  );
}
