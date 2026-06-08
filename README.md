# MealMind 🍽️

> AI application that creates customized meal plans based on the groceries you
> already have — to promote sustainability and zero food wastage.

**The meal planner that uses up what you already have.** Add your pantry (with
expiry dates), set your health goals — an AI **agent** plans a week of meals that
prioritizes ingredients about to spoil, minimizing food waste and your grocery
bill, then self-corrects against your calorie and allergy constraints.

Built as a polyglot, agentic, full-stack project:

```
┌─────────────┐   REST/JSON   ┌──────────────────┐   HTTP    ┌─────────────────────┐
│   React     │ ────────────▶ │   Spring Boot    │ ────────▶ │  Python AI service  │
│  (web/)     │ ◀──────────── │   API (api/)     │ ◀──────── │  FastAPI + LangGraph │
│  pantry UI  │               │  orchestration,  │           │  (ai-service/)      │
│  + waste    │               │  validation,     │           │  plan→check→re-plan │
│  dashboard  │               │  error handling  │           └──────────┬──────────┘
└─────────────┘               └──────────────────┘                      │
                                                                  ┌──────▼──────┐
                                                                  │ Claude API  │
                                                                  │ (Sonnet 4.6)│
                                                                  └─────────────┘
```

## The signature feature: a "use it up" agent
Most meal planners ignore your fridge. MealMind optimizes *around* it. The agent's
constraint loop enforces three things and **re-plans** if any fail:

1. **Pantry utilization** — the plan must use at least half of what you have.
2. **Rescue expiring items** — anything within 3 days of its expiry date *must* be
   used, or the agent tries again.
3. Allergies + a calorie band around your target.

The result includes a **waste report**: % of pantry used, expiring items rescued,
and what's still going unused.

## Why this architecture (the recruiter story)
- **LangGraph/LangChain are Python**, so the agent lives in its own FastAPI service.
- **Spring Boot** owns orchestration, validation, error handling (clean 4xx/5xx,
  no stack traces), and — from Week 3 — auth + persistence.
- **The agent is a deterministic state machine**, not "ask the LLM if the plan is
  good." The `plan → check_limits → re-plan` back-edge is real self-correction.
- **The LLM is injectable**, so the entire agent is tested with a fake LLM —
  no API key, fully deterministic. (See `ai-service/tests/`.)

## The agent graph
```
parse_request → plan_meals → check_limits ──fail──▶ (back to plan_meals, max 3×)
                                  │ pass
                                  ▼
                          compute_waste → grocery_list → END
```

## Quick start (local)
```bash
cp .env.example .env          # paste your ANTHROPIC_API_KEY into .env
docker compose up --build     # starts Postgres + AI service + API + web
```
Open:
- Web app:         http://localhost:5173
- API health:      http://localhost:8080/actuator/health
- AI service docs: http://localhost:8000/docs

Full instructions, including running services individually: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Tests
| Service | Command | Coverage |
|---|---|---|
| AI service | `cd ai-service && pytest` | tools, constraint checker, **full agent loop with fake LLM** (14 tests) |
| API | `cd api && ./mvnw test` | controller validation, happy path, AI-service-down handling (3 tests) |

## Repository layout
| Path          | Service              | Stack                          |
|---------------|----------------------|--------------------------------|
| `web/`        | Frontend             | React + Vite                   |
| `api/`        | Backend API          | Spring Boot 3 (Java 17)        |
| `ai-service/` | Agent                | FastAPI + LangGraph + Claude   |

## Going live (free tier)
- Backend (API + AI service): [render.yaml](render.yaml) blueprint → Render
- Frontend: [web/vercel.json](web/vercel.json) → Vercel
- Steps: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) §6

## Project docs
- [docs/ROADMAP.md](docs/ROADMAP.md) — week-by-week build plan
- [docs/SENIOR_REVIEW.md](docs/SENIOR_REVIEW.md) — self-review + what's deferred
