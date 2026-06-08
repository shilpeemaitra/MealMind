# Getting Started

You just got a working 3-service scaffold. Here's how to run it and what to do next.

## 1. Prerequisites (one-time)
- **Docker Desktop** running (you have it ✓)
- **An Anthropic API key** — https://console.anthropic.com → Settings → API Keys
- **(For non-Docker frontend dev) Node 20** — your machine has Node 18, which Vite 5
  won't run. Bump it:
  ```bash
  nvm install 20 && nvm use 20      # or: brew install node@20
  ```
  (You don't need this if you only ever run the frontend via Docker.)

## 2. Run the whole stack
```bash
cd ~/mealmind
cp .env.example .env                # then paste your ANTHROPIC_API_KEY into .env
docker compose up --build           # first build takes a few minutes
```
Open:
- **Web app:**        http://localhost:5173
- **API health:**     http://localhost:8080/actuator/health
- **AI service docs:** http://localhost:8000/docs  ← try the agent directly here

Type a goal + pantry on the web app and hit **Generate plan**. The request flows
React → Spring Boot → Python agent → Claude → back. 🎉

## 3. Run services individually (faster iteration)
Useful when you're editing one service and don't want full rebuilds.

**AI service:**
```bash
cd ai-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload --port 8000
```

**Spring Boot API:**
```bash
cd api
AI_SERVICE_URL=http://localhost:8000 ./mvnw spring-boot:run
```

**Frontend (needs Node 20):**
```bash
cd web
npm install
npm run dev
```

## 4. Test the agent without the UI
With the AI service running, hit it directly:
```bash
curl -s http://localhost:8000/agent/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "goal": "lose weight",
    "daily_calorie_target": 1800,
    "dietary_pattern": "vegetarian",
    "allergies": ["peanuts"],
    "pantry": ["rice", "eggs", "spinach"],
    "days": 2
  }' | python3 -m json.tool
```

## 5. What's wired vs. what's stubbed
| Piece | Status |
|---|---|
| React form → API → agent → Claude → back | ✅ working |
| LangGraph plan→check→re-plan loop | ✅ working (calorie + allergen constraints) |
| Nutrition lookup | ⚙️ local table (upgrade to USDA API later) |
| Auth + saving plans | 🔜 Week 3 (JPA is on the classpath, auto-config disabled for now) |
| Deploy to live URLs | 🔜 Week 1 task — see below |

## 6. Going live (all free)
| Service | Host | How |
|---|---|---|
| `web/` | **Vercel** | Import the repo, set root to `web/`, add `VITE_API_BASE_URL` env var |
| `api/` | **Render** | New Web Service → Docker → root `api/` |
| `ai-service/` | **Render** | New Web Service → Docker → root `ai-service/`, add `ANTHROPIC_API_KEY` |
| Postgres | **Neon** | Create a DB, paste its connection string into the API's env |

Push to GitHub first:
```bash
gh repo create mealmind --public --source=. --remote=origin --push
```

## Next: build the agent out (Week 2)
See [ROADMAP.md](ROADMAP.md). The first real task is making the constraint checker
richer and exposing the tools to the LLM so it can call them mid-reasoning.
