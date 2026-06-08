const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

/**
 * POST a plan request to the Spring Boot API. Returns the parsed plan, or throws
 * an Error with a user-friendly message derived from the API's JSON error shape.
 */
export async function generatePlan(request) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error("Can't reach the server. Is the API running?");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorMessage(res.status, body));
  }
  return res.json();
}

function errorMessage(status, body) {
  if (body?.error === "ai_service_unavailable") {
    return "The meal-planning agent is starting up or unreachable. Try again in a moment.";
  }
  if (body?.error === "validation_failed") {
    const fields = body.detail ? Object.values(body.detail).join("; ") : "";
    return `Please check your inputs. ${fields}`;
  }
  return `Request failed (${status}). Please try again.`;
}
