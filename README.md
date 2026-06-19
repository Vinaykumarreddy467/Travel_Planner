# 🧳 AI Travel Planner

AI travel planning chat app with a React frontend and a FastAPI backend. It uses **Groq** for responses, **OpenWeatherMap** for weather-aware context, and **OpenStreetMap / Nominatim / Overpass** for real place lookups.

## Features

- 🤖 **Chat-based trip planning** — ask for itineraries, destination ideas, or travel advice
- 🌤️ **Weather-aware suggestions** — the backend adds forecast context when it can
- 📍 **Real place references** — attractions, restaurants, and hotels come from OpenStreetMap data
- 💬 **Conversation history** — the frontend keeps the chat thread in sync with the backend
- 🔁 **Local dev proxy** — Vite forwards `/chat` requests to FastAPI on port `8000`

## What You Need

| Service | Purpose | Cost |
|---|---|---|
| **Groq** | LLM responses | Free tier available |
| **OpenWeatherMap** | Weather forecast context | Free tier available |
| **OpenStreetMap / Nominatim / Overpass** | Place lookup data | Free |

## Environment Variables

Create a `.env` file in the project root with at least:

- `GROQ_API_KEY` - required for chat responses
- `GROQ_MODEL` - optional, defaults to `llama-3.3-70b-versatile`
- `OWM_API_KEY` - optional, enables weather context

## Setup

### 1. Install dependencies

```bash
cd /home/mikealson/Open Work/travel-planner

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install fastapi uvicorn

cd frontend
npm install
cd ..
```

### 2. Add API keys

```bash
cp .env.example .env
# Edit .env and add your keys
```

### 3. Start the backend

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## How It Works

The React app sends chat messages to `POST /chat`. The FastAPI backend builds a travel-planning prompt, adds optional weather and place context, and sends the request to Groq. If place data is available, the reply also includes OpenStreetMap links.

## Project Structure

```text
travel-planner/
├── backend/
│   └── main.py        # FastAPI chat API
├── frontend/
│   ├── src/
│   │   ├── App.jsx    # Chat UI
│   │   └── App.css    # App styling
│   ├── package.json   # Frontend dependencies and scripts
│   └── vite.config.js # Dev server proxy to backend
├── src/
│   ├── config.py      # Environment loading
│   ├── models.py      # Shared data models
│   ├── weather.py     # OpenWeatherMap integration
│   ├── places.py      # OpenStreetMap place lookup
│   └── llm_client.py  # Groq client helpers
├── planner.ipynb      # Legacy notebook / exploration
├── requirements.txt   # Python dependencies
└── output/            # Generated artifacts
```

## Backend Endpoint

- `GET /` returns a simple health check
- `POST /chat` accepts `{ "message": "...", "history": [...] }` and returns `{ "reply": "..." }`
