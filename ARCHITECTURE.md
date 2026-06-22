# Architecture

## System Overview

```mermaid
flowchart TB
    subgraph Browser["🌐 Browser"]
        UI["React Chat UI<br/>port 5173 (dev)"]
    end

    subgraph Server["🖥️ FastAPI Server — port 8000"]
        direction TB
        API["FastAPI App<br/>backend/main.py"]
        STATIC["Static Files<br/>frontend/dist/ (prod only)"]
        CHAT["POST /chat<br/>SSE Streaming Endpoint"]
        HEALTH["GET /health<br/>Health Check"]
    end

    subgraph Services["☁️ External Services"]
        GROQ["Groq API<br/>LLM (streaming)"]
        GMAPS["Google Maps<br/>Places API (New)"]
        OWM["OpenWeatherMap<br/>Weather Forecast"]
        OSM["OpenStreetMap<br/>Nominatim + Overpass<br/>(fallback)"]
    end

    subgraph Python["🐍 Python Modules — src/"]
        CONFIG["config.py<br/>Env vars & settings"]
        MODELS["models.py<br/>Pydantic schemas"]
        PLACES["places.py<br/>GMaps → OSM fallback"]
        GMAPSCLIENT["google_maps.py<br/>Places API client"]
        WEATHER["weather.py<br/>Forecast + advice"]
        LLM["llm_client.py<br/>Groq client"]
        PLANNER["planner.py<br/>Orchestrator"]
    end

    %% --- Connections ---
    UI -->|"fetch('/chat')"| CHAT
    UI -->|"/ (root)"| STATIC

    CHAT --> PLACES
    CHAT --> WEATHER
    CHAT --> LLM

    PLACES -->|"key configured"| GMAPSCLIENT
    PLACES -->|"empty / no key"| OSM
    GMAPSCLIENT --> GMAPS
    WEATHER --> OWM
    LLM --> GROQ

    CONFIG -.-> PLACES
    CONFIG -.-> GMAPSCLIENT
    CONFIG -.-> WEATHER
    MODELS -.-> PLACES
    MODELS -.-> GMAPSCLIENT
    MODELS -.-> WEATHER

    %% --- Styling ---
    classDef browser fill:#1a1a2e,stroke:#e94560,stroke-width:2px,color:#eee
    classDef server fill:#16213e,stroke:#0f3460,stroke-width:2px,color:#eee
    classDef external fill:#1a1a2e,stroke:#e94560,stroke-width:1px,color:#ddd,stroke-dasharray: 5 5
    classDef module fill:#0f3460,stroke:#533483,stroke-width:1px,color:#eee

    class UI browser
    class API,STATIC,CHAT,HEALTH server
    class GROQ,GMAPS,OWM,OSM external
    class CONFIG,MODELS,PLACES,GMAPSCLIENT,WEATHER,LLM,PLANNER module
```

## Request Flow

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant UI as 🖥️ React UI
    participant API as 🐍 FastAPI
    participant Groq as 🤖 Groq LLM
    participant Maps as 🗺️ Google Maps
    participant OSM as 🌍 OpenStreetMap
    participant Weather as 🌤️ OpenWeatherMap

    User->>UI: Type "Plan a trip to Paris"
    UI->>API: POST /chat { message, history }

    Note over API: Extract destination: "Paris"

    par Fetch Weather
        API->>Weather: get_forecast("Paris")
        Weather-->>API: Weather data
    and Fetch Places
        API->>Maps: searchText("attractions in Paris")
        alt Maps returns results
            Maps-->>API: Places with ratings, prices
        else Maps fails / empty
            API->>OSM: Overpass query
            OSM-->>API: Places (no ratings)
        end
    end

    Note over API: Build system prompt with context
    API->>Groq: chat.completions.create(stream=True)

    loop Each token
        Groq-->>API: delta content
        API-->>UI: SSE data: { chunk: "..." }
        UI-->>User: Render text word-by-word
    end

    API-->>UI: SSE data: { maps: "Google Maps refs..." }
    UI-->>User: Show clickable map links
    API-->>UI: SSE data: { done: true }
    UI-->>User: Enable input + Copy button
```

## Streaming Format (SSE)

```
POST /chat  →  Server-Sent Events stream

data: {"chunk":"Paris"}
data: {"chunk":" is"}
data: {"chunk":" a"}
data: {"chunk":" beautiful"}
data: {"chunk":" city"}
data: {"maps":"Google Maps references:\n- Eiffel Tower: https://..."}
data: {"done":true}
```

## Place Lookup Fallback Chain

```mermaid
flowchart LR
    REQ["Search Places"] --> GMAPS{"Google Maps key set?"}
    GMAPS -->|"Yes"| TRY["Try Google Maps API"]
    GMAPS -->|"No"| OSM["Use OpenStreetMap"]

    TRY --> CHECK{"Returned results?"}
    CHECK -->|"Yes ✅"| DONE["Return places<br/>with ratings, prices"]
    CHECK -->|"Empty / Error"| OSM

    OSM --> GEOCODE["Geocode city → coords<br/>(Nominatim)"]
    GEOCODE --> OVERPASS["Query Overpass API"]
    OVERPASS --> FALLBACKDONE["Return places<br/>(no ratings)"]
```

## Project Structure

```
travel-planner/
│
├── backend/
│   └── main.py              # FastAPI server — routes, SSE streaming, context building
│
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── App.jsx          # Chat UI — SSE reader, message renderer, linkify
│   │   ├── App.css          # Premium dark theme
│   │   └── main.jsx         # Entry point
│   ├── vite.config.js       # Proxy /chat → localhost:8000 (dev only)
│   └── package.json
│
├── src/                      # Shared Python modules
│   ├── config.py            # Environment variables from .env
│   ├── models.py            # Pydantic data models (Place, Weather, TravelPlan...)
│   ├── google_maps.py       # Google Maps Places API (New) client
│   ├── places.py            # Place lookup — GMaps first, OSM fallback
│   ├── weather.py           # OpenWeatherMap forecast + advice
│   ├── llm_client.py        # Groq LLM client
│   └── planner.py           # Orchestrator combining all sources
│
├── Dockerfile                # Single-image deploy (Python + Node + React build)
├── render.yaml               # Render blueprint (one-click deploy)
├── start.sh                  # Start app locally (dev or production mode)
├── stop.sh                   # Stop all processes
├── .env.example              # Template for API keys
├── requirements.txt
└── README.md
```

## Key Design Decisions

| Decision | Why |
|---|---|
| **SSE over WebSocket** | Simpler protocol, no extra library, works with `ReadableStream` in the browser |
| **Google Maps first → OSM fallback** | Google provides ratings, price levels, open/closed status; OSM is a reliable free fallback |
| **AsyncGroq with streaming** | Token-by-token responses for a smooth chat UX |
| **Single Docker image** | One service to deploy = simpler ops, fewer things to break |
| **FastAPI serves frontend** | No separate static hosting needed in production |
| **Pydantic models** | Type safety and validation shared across all modules |
