import { useEffect, useState } from "react";
import { generatePlan } from "./api";
import PantryEditor from "./PantryEditor";
import WasteDashboard from "./WasteDashboard";

const DEFAULT_PANTRY = [
  { name: "rice", quantity: "500g", expires_on: "" },
  { name: "spinach", quantity: "1 bag", expires_on: soonDate(2) },
  { name: "eggs", quantity: "6", expires_on: "" },
  { name: "oats", quantity: "", expires_on: "" },
];

export default function App() {
  const [goal, setGoal] = useState("lose weight");
  const [calories, setCalories] = useState(1800);
  const [diet, setDiet] = useState("vegetarian");
  const [allergies, setAllergies] = useState("peanuts");
  const [days, setDays] = useState(3);
  const [pantry, setPantry] = useState(DEFAULT_PANTRY);

  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(navigator.onLine);

  // PWA: surface offline state so the user knows why a plan request might fail
  // (generating a plan needs the network — it calls the agent + Claude).
  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setPlan(null);
    try {
      const request = {
        goal,
        daily_calorie_target: Number(calories),
        dietary_pattern: diet,
        allergies: csv(allergies),
        pantry: pantry
          .filter((p) => p.name.trim())
          .map((p) => ({
            name: p.name.trim(),
            quantity: p.quantity?.trim() || "",
            expires_on: p.expires_on || null,
          })),
        days: Number(days),
        today: new Date().toISOString().slice(0, 10),
      };
      setPlan(await generatePlan(request));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      {!online && (
        <div className="offline-banner">📡 You're offline — connect to generate a plan.</div>
      )}
      <header>
        <h1>MealMind 🍽️</h1>
        <p className="tagline">
          The meal planner that <strong>uses up what you already have</strong>.
          Add your pantry, set your goals — the agent plans around what's expiring
          to cut food waste and your grocery bill.
        </p>
      </header>

      <form onSubmit={onSubmit}>
        <div className="card grid2">
          <label>
            Goal
            <input value={goal} onChange={(e) => setGoal(e.target.value)} />
          </label>
          <label>
            Daily calories
            <input
              type="number"
              value={calories}
              onChange={(e) => setCalories(e.target.value)}
            />
          </label>
          <label>
            Dietary pattern
            <input value={diet} onChange={(e) => setDiet(e.target.value)} />
          </label>
          <label>
            Allergies (comma-separated)
            <input value={allergies} onChange={(e) => setAllergies(e.target.value)} />
          </label>
          <label>
            Days
            <input
              type="number"
              min="1"
              max="7"
              value={days}
              onChange={(e) => setDays(e.target.value)}
            />
          </label>
        </div>

        <div className="card">
          <PantryEditor pantry={pantry} onChange={setPantry} />
        </div>

        <button type="submit" disabled={loading || !online} className="primary">
          {loading ? "Agent is planning…" : "Generate plan"}
        </button>
      </form>

      {error && <p className="error">⚠️ {error}</p>}

      {plan && (
        <section className="results">
          <WasteDashboard report={plan.waste_report} />

          {plan.notes && <p className="notes">{plan.notes}</p>}
          {plan.revisions > 1 && (
            <p className="meta">
              🔁 The agent re-planned {plan.revisions - 1} time
              {plan.revisions - 1 === 1 ? "" : "s"} to satisfy your constraints.
            </p>
          )}

          <div className="days">
            {plan.days.map((day) => (
              <div key={day.day} className="card day">
                <h3>
                  {day.day} <span className="cals">{day.total_calories} cal</span>
                </h3>
                {day.meals.map((meal, i) => (
                  <div key={i} className="meal">
                    <div className="meal-head">
                      <strong>{meal.name}</strong>
                      <span className="cals">{meal.calories} cal</span>
                    </div>
                    <div className="ingredients">
                      {meal.ingredients.map((ing, j) => (
                        <span
                          key={j}
                          className={
                            (meal.uses_pantry || []).some((p) =>
                              ing.toLowerCase().includes(p.toLowerCase())
                            )
                              ? "ing from-pantry"
                              : "ing"
                          }
                        >
                          {ing}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="card">
            <h3>🛒 Grocery list</h3>
            {plan.grocery_list.length ? (
              <ul className="grocery">
                {plan.grocery_list.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>You already have everything you need! 🎉</p>
            )}
          </div>

          <p className="legend">
            <span className="ing from-pantry">highlighted</span> = used from your pantry
          </p>
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

function soonDate(daysFromNow) {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  return d.toISOString().slice(0, 10);
}
