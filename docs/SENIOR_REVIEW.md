# Senior Engineering Review — MealMind v0.2

Reviewed as if this were a PR from a mid-level engineer. Verdict: **solid bones,
genuinely novel feature, ships.** But several things would bite in production or
embarrass in an interview. Grouped by severity.

## 🔴 Must-fix (correctness / will break in prod)

1. **AI service has no error handling around the LLM call.** If Claude returns
   malformed JSON, times out, or the key is missing, `run_plan` throws and FastAPI
   returns a 500 with a stack trace. The graph already tolerates empty plans
   (`_extract_json_array` returns `[]`), but an auth error or network blip is
   unhandled. → Wrap the route; return a clean 502/503.

2. **`_extract_json_array` silently returns `[]` on parse failure.** An empty plan
   then sails through `check_limits` (no days = no violations) and the user gets a
   blank plan with a 100% "waste score" — actively misleading. → Treat an empty
   draft as a violation so the agent re-plans; if still empty, surface an error.

3. **No retry/backoff on the Anthropic call.** Transient 429/529 (common on free
   tier) will fail the whole request. langchain-anthropic supports `max_retries`.
   → Set it.

## 🟠 Should-fix (quality / interview credibility)

4. **`missing_from_pantry` dedupes by exact lowercased string.** "2 eggs" and
   "3 eggs" are treated as different grocery items → duplicate-ish grocery lines.
   Minor, but a sharp interviewer will spot it. (Acceptable for v1; note it.)

5. **No tests on the Spring Boot layer.** The Java side has zero tests. At minimum
   a controller test (validation → 400, happy path with a mocked client) and an
   exception-handler test. Recruiters look for tests on *every* layer.

6. **`README` still describes the old (pre-pantry) product.** The architecture
   diagram doesn't mention the waste report. Docs drift = looks unmaintained.

7. **Datasource is disabled but `render.yaml` wires a Postgres + connection string.**
   Render's `connectionString` is `postgres://...`, which Spring's JDBC driver
   rejects (`jdbc:postgresql://` required). Since JPA is currently excluded this is
   inert, but it's a landmine for Week 3. → Document loudly; don't wire env that
   isn't consumed yet, OR add the URL-rewrite now.

## 🟡 Nice-to-have (polish)

8. **No request logging / observability.** A `revisions`-count log line per request
   would make the agent's behavior visible in Render logs (cheap LangSmith stand-in).

9. **Frontend has no loading skeleton** — just a button label change. A spinner or
   skeleton during the (potentially 10–30s) agent call would feel far better.

10. **2 moderate npm audit vulns** (esbuild/vite dev-server, dev-only). Not
    shippable-blocking but worth a note + `npm audit` mention.

11. **No `.dockerignore`** files → Docker build context includes `.venv/`,
    `node_modules/`, `target/`. Slower builds, fatter context. → Add them.

## ✅ What's genuinely good (keep)
- The injectable-LLM design enabling **keyless, deterministic agent tests** is the
  strongest engineering signal here. Most portfolio "agent" projects can't test
  their agent at all.
- The plan→check→re-plan loop with a *deterministic* constraint checker (not "ask
  the LLM if it's good") is the right architecture and a great whiteboard story.
- Clean service separation; snake_case contract handled centrally; resilient API
  client with timeout + typed error handling.
- The waste report is a real, quantified, novel feature — not a gimmick.

## Decision
Fix all 🔴, fix #5/#6/#7 from 🟠 (tests, docs, the Postgres landmine), and #11
(.dockerignore) from 🟡. Defer #4, #8, #9, #10 to a tracked follow-up — they're
real but not worth blocking the first live deploy.
