# MealMind — Build Roadmap (3–4 weeks to live)

Guiding principle: **deploy an empty app first**, then add features. Shipping early kills
the #1 portfolio-project failure mode (never going live).

## Week 1 — Skeleton + deploy
- [x] Monorepo scaffold (web / api / ai-service) + docker-compose
- [ ] Bump local Node 18 → 20 (`nvm install 20 && nvm use 20`) — Vite needs it
- [ ] `docker compose up` runs all 4 containers locally
- [ ] Wire the happy path: React → Spring Boot `/api/plan` → Python `/agent/plan` → Claude → back
- [ ] Deploy *empty* services: web → Vercel, api + ai-service → Render, db → Neon

## Week 2 — The agent core (the heart)
- [ ] LangGraph state graph: parse_request → plan_meals → check_limits → (re-plan loop) → grocery_list
- [ ] Tool 1: `nutrition_lookup` (start with a static/local table, upgrade later)
- [ ] Tool 2: `pantry_check` (what's missing vs. what they have)
- [ ] Constraint checker: calories, allergies, dietary rules → triggers re-plan on failure
- [ ] Spring Boot orchestration + DTOs that match the agent's JSON contract

## Week 3 — Product polish
- [ ] Auth (JWT) + user accounts in Spring Boot
- [ ] Save / load plans (Postgres via JPA)
- [ ] Chat-style re-planning UI ("make Tuesday a 10-min dinner")
- [ ] Grocery list view

## Week 4 — Recruiter shine
- [ ] LangSmith tracing (visualize the agent's decisions — great in interviews)
- [ ] README with architecture diagram + demo GIF + live link
- [ ] Short "how the agent works" write-up
- [ ] Polish empty/error/loading states

## Agent concepts cheat-sheet (you're new to this — keep handy)
- **Agent** = an LLM run in a loop that can call **tools** (functions you wrote) and decide what to do next.
- **Tool** = a typed function the model can invoke (e.g. `nutrition_lookup("oats")`).
- **LangGraph** = models that loop as a *graph*: nodes = steps, edges = decisions about where to go next.
- **State** = a shared dict passed between nodes (goals, pantry, the draft plan, validation errors).
- **The agentic bit** = `check_limits` can route *back* to `plan_meals` — self-correction, not one-shot.
