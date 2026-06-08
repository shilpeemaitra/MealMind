/**
 * Editable pantry list — the heart of the 'use it up' feature. Each row is an
 * ingredient with an optional expiry date. Items expiring soon are highlighted
 * so the user (and the agent) know what to prioritize.
 */
const SOON_DAYS = 3;

export default function PantryEditor({ pantry, onChange }) {
  function update(index, field, value) {
    const next = pantry.map((item, i) =>
      i === index ? { ...item, [field]: value } : item
    );
    onChange(next);
  }

  function addRow() {
    onChange([...pantry, { name: "", quantity: "", expires_on: "" }]);
  }

  function removeRow(index) {
    onChange(pantry.filter((_, i) => i !== index));
  }

  return (
    <div className="pantry">
      <div className="pantry-head">
        <h3>🥫 Your pantry</h3>
        <span className="hint">The agent plans meals to use these up first.</span>
      </div>

      {pantry.map((item, i) => {
        const soon = isExpiringSoon(item.expires_on);
        return (
          <div className={`pantry-row ${soon ? "soon" : ""}`} key={i}>
            <input
              className="pantry-name"
              placeholder="ingredient"
              value={item.name}
              onChange={(e) => update(i, "name", e.target.value)}
            />
            <input
              className="pantry-qty"
              placeholder="qty (optional)"
              value={item.quantity}
              onChange={(e) => update(i, "quantity", e.target.value)}
            />
            <input
              className="pantry-date"
              type="date"
              value={item.expires_on}
              onChange={(e) => update(i, "expires_on", e.target.value)}
              title="Expiry date (optional)"
            />
            {soon && <span className="soon-badge" title="Expiring soon">⚠️</span>}
            <button
              type="button"
              className="ghost"
              onClick={() => removeRow(i)}
              aria-label="Remove item"
            >
              ✕
            </button>
          </div>
        );
      })}

      <button type="button" className="ghost add" onClick={addRow}>
        + Add ingredient
      </button>
    </div>
  );
}

function isExpiringSoon(dateStr) {
  if (!dateStr) return false;
  const expires = new Date(dateStr);
  if (Number.isNaN(expires.getTime())) return false;
  const diffDays = (expires - new Date()) / (1000 * 60 * 60 * 24);
  return diffDays <= SOON_DAYS;
}
