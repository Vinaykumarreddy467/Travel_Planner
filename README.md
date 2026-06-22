# AI Travel Planner

AI travel planning chat app with a React frontend and a FastAPI backend. Responses stream word-by-word via SSE. Uses **Groq** for LLM responses, **Google Maps Places API (New)** for place data (with **OpenStreetMap** fallback), and **OpenWeatherMap** for weather-aware context.

## Features

- **Streaming chat** — responses appear token-by-token as Groq generates them
- **Google Maps places** — real attractions, restaurants, and hotels with ratings, price levels, and open/closed status
- **Automatic fallback** — if Google Maps is unavailable, seamlessly falls back to OpenStreetMap (Nominatim + Overpass)
- **Weather-aware suggestions** — backend adds forecast context when a destination is detected
- **Conversation history** — the frontend keeps the chat thread in sync with the backend
- **Premium dark theme** — amber-and-emerald design with pill-shaped suggestion chips, smooth animations, copy-to-clipboard

## What You Need

| Service | Purpose | Cost |
|---|---|---|
| **Groq** | LLM responses (streaming) | Free tier available |
| **Google Maps Places API (New)** | Place lookup (ratings, prices, hours) | $200/month free credit |
| **OpenWeatherMap** | Weather forecast context | Free tier available |
| **OpenStreetMap** | Fallback place data (no API key needed) | Free |

## Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | API key for Groq LLM |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model to use |
| `OWM_API_KEY` | No | — | Enables weather forecast context |
| `GOOGLE_MAPS_API_KEY` | No | — | Enables Google Maps places (falls back to OSM if absent) |

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### 2. Add API keys

```bash
cp .env.example .env
# Edit .env and add your keys (at minimum GROQ_API_KEY)
```

### 3. Start the backend (port 8000)

```bash
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 4. Start the frontend (port 5173)

```bash
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## Run in Production (single command)

Build the frontend and serve everything from FastAPI on one port:

```bash
# Build the React app
cd frontend && npm install && npm run build && cd ..

# Start the unified server (API + UI at http://localhost:8000)
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Visit **http://localhost:8000** — the chat UI is served directly by FastAPI.

## Deploy to Render (free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### One-click deploy

1. Fork or push this repo to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com)
3. Click **New +** → **Blueprint**
4. Connect your GitHub repo
5. Render auto-detects `render.yaml` — click **Apply**
6. After deploy, add your API keys in the **Environment** section:
   - `GROQ_API_KEY` (required)
   - `GOOGLE_MAPS_API_KEY` (optional, enables Google Maps places)
   - `OWM_API_KEY` (optional, enables weather context)
7. Click **Manual Deploy** → **Clear build cache & deploy**

Your app will be at `https://travel-planner.onrender.com`.

### Or deploy with Docker locally

```bash
docker build -t travel-planner .
docker run -p 8000:8000 --env-file .env travel-planner
```

Visit **http://localhost:8000**.

## How It Works

1. The user types a message in the React chat UI.
2. The frontend sends `POST /chat` with `{ "message": "...", "history": [...] }`.
3. The backend extracts the destination (e.g. "Paris"), fetches weather and places in parallel, then builds a system prompt with that context.
4. The backend calls Groq with `stream=True` and pipes each token back as a Server-Sent Event.
5. After the AI text, the backend appends a "Google Maps references" (or "OpenStreetMap references") section with clickable map links.
6. The frontend renders text as it arrives, then displays the maps section and a Copy button.

### Streaming format (SSE)

```
data: {"chunk":"Paris"}
data: {"chunk":" is"}
data: {"chunk":" wonderful"}
data: {"maps":"Google Maps references:\n- Eiffel Tower: https://..."}
data: {"done":true}
```

## Place lookup fallback chain

```
Search places
  ├── Google Maps Places API (New) ── has results? → ✅ return
  │                                    empty/error? → ⬇️ fall through
  └── OpenStreetMap (Nominatim + Overpass) → return results
```

## Project Structure

```text
travel-planner/
├── backend/
│   └── main.py              # FastAPI chat API with SSE streaming
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js       # Dev proxy /chat → localhost:8000
│   └── src/
│       ├── main.jsx
│       ├── App.jsx          # Chat UI with SSE reader, linkify, copy
│       └── App.css          # Premium dark theme
├── src/
│   ├── config.py            # Environment variables (from .env)
│   ├── models.py            # Pydantic data models
│   ├── google_maps.py       # Google Maps Places API (New) client
│   ├── places.py            # Place lookup (GMaps → OSM fallback chain)
│   ├── weather.py           # OpenWeatherMap forecast + advice
│   ├── llm_client.py        # Groq LLM client helpers
│   └── planner.py           # Orchestrator combining all sources
├── planner.ipynb            # Legacy exploration notebook
├── .env.example             # Template for environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the React chat UI (when frontend is built) |
| `GET` | `/health` | Health check (`{"status":"ok","app":"AI Travel Planner"}`) |
| `POST` | `/chat` | Send a message, receive SSE stream (see format above) |

The `/chat` endpoint accepts:
```json
{
  "message": "Plan a 5-day trip to Tokyo",
  "history": [
    {"role": "user", "content": "I love sushi"},
    {"role": "assistant", "content": "Great! Let's plan..."}
  ]
}
```

Returns a Server-Sent Events stream:
```
data: {"chunk":"Tokyo"}
data: {"chunk":" is"}
data: {"chunk":" incredible"}
data: {"maps":"Google Maps references:\n- ..."}
data: {"done":true}
```
