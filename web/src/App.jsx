import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

export default function App() {
  const [form, setForm] = useState({
    goal: "lose weight",
    daily_calorie_target: 1800,
    dietary_pattern: "vegetarian",
    allergies: "peanuts",
    pantry: "rice, eggs, spinach, olive oil",
    days: 3,
  });
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function generate(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setPlan(null);
    try {
      const body = {
        goal: form.goal,
        daily_calorie_target: Number(form.daily_calorie_target),
        dietary_pattern: form.dietary_pattern,
        allergies: csv(form.allergies),
        pantry: csv(form.pantry),
        days: Number(form.days),
      };
      const res = await fetch(`${API_BASE}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setPlan(await res.json());
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <h1>MealMind 🍽️</h1>
      <p className="tagline">
        Tell it your goals + what's in your kitchen. The agent plans your meals,
        checks the constraints, and re-plans if needed.
      </p>

      <form onSubmit={generate} className="card">
        <label>
          Goal
          <input value={form.goal} onChange={(e) => update("goal", e.target.value)} />
        </label>
        <label>
          Daily calorie target
          <input
            type="number"
            value={form.daily_calorie_target}
            onChange={(e) => update("daily_calorie_target", e.target.value)}
          />
        </label>
        <label>
          Dietary pattern
          <input
            value={form.dietary_pattern}
            onChange={(e) => update("dietary_pattern", e.target.value)}
          />
        </label>
        <label>
          Allergies (comma-separated)
          <input value={form.allergies} onChange={(e) => update("allergies", e.target.value)} />
        </label>
        <label>
          Pantry (comma-separated)
          <input value={form.pantry} onChange={(e) => update("pantry", e.target.value)} />
        </label>
        <label>
          Days
          <input
            type="number"
            min="1"
            max="7"
            value={form.days}
            onChange={(e) => update("days", e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Planning…" : "Generate plan"}
        </button>
      </form>

      {error && <p className="error">⚠️ {error}</p>}

      {plan && (
        <section>
          {plan.notes && <p className="notes">{plan.notes}</p>}
          <p className="meta">Agent re-planned {plan.revisions} time(s).</p>

          <div className="days">
            {plan.days.map((day) => (
              <div key={day.day} className="card day">
                <h3>
                  {day.day} <span className="cals">{day.total_calories} cal</span>
                </h3>
                {day.meals.map((meal, i) => (
                  <div key={i} className="meal">
                    <strong>{meal.name}</strong> <span className="cals">{meal.calories} cal</span>
                    <div className="ingredients">{meal.ingredients.join(", ")}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="card">
            <h3>🛒 Grocery list</h3>
            {plan.grocery_list.length ? (
              <ul>
                {plan.grocery_list.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>You already have everything you need!</p>
            )}
          </div>
        </section>
      )}
    </main>
  );
}

function csv(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}
