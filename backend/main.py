"""
FastAPI Backend for the AI Travel Planner Chat.
Handles chat messages, streams responses from Groq SSE, appends weather & places context.
"""

import sys
import os
import re
import json
import asyncio
from dotenv import load_dotenv

# Add parent dir so we can import the 'src' modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load API keys from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from groq import AsyncGroq
import os

from src.places import get_hotels, get_top_attractions, get_top_restaurants, get_gmaps_link
from src.config import settings
from src.weather import get_forecast, weather_advice

# Load API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Create FastAPI app
app = FastAPI(title="AI Travel Planner Chat")

# Allow the React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────
#  SERVE BUILT FRONTEND (for production)
# ──────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    print(f"[server] serving built frontend from {FRONTEND_DIR}")
else:
    print("[server] frontend/dist not found — API only (run 'cd frontend && npm run build' to build UI)")

# ──────────────────────────────────────────
#  DATA MODELS (what the API expects/returns)
# ──────────────────────────────────────────


class ChatRequest(BaseModel):
    """What the user sends to the API."""
    message: str
    history: list[dict] = []  # Previous messages: [{"role": "user/assistant", "content": "..."}]


class ChatResponse(BaseModel):
    """What the API sends back."""
    reply: str


# ──────────────────────────────────────────
#  SYSTEM PROMPT (the AI's personality)
# ──────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert travel planner AI assistant. Your job is to help users plan amazing trips.

You can:
- Suggest destinations based on preferences
- Create day-by-day itineraries
- Recommend restaurants, attractions, and hotels
- Give budget advice and cost estimates
- Provide travel tips (best time to visit, local customs, packing advice)
- Answer questions about cities, countries, and cultures

Be conversational, friendly, and helpful. When suggesting an itinerary, 
be specific with place names, estimated costs, and practical tips.

If the user asks about something outside travel planning, 
politely steer the conversation back to travel.

Keep responses concise but informative. Use emojis sparingly for visual appeal.
"""


def extract_destination(message: str) -> str | None:
    """Extract a likely travel destination from a user message."""
    patterns = [
        r"(?:travel|trip|visit|go|plan(?: a)? trip to|plan(?: a)? trip for|suggest(?:ions)? for)\s+([A-Za-z][A-Za-z\s,'-]+)",
        r"(?:to|in)\s+([A-Z][A-Za-z\s,'-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            destination = match.group(1).strip()
            destination = re.sub(r"[?.!,]+$", "", destination).strip()
            if destination:
                return destination

    return None


def build_weather_context(destination: str) -> str:
    """Build a short weather summary for prompt context."""
    forecast = get_forecast(destination, days=3)
    if not forecast:
        return f"Weather data for {destination} is unavailable right now."

    first_day = forecast[0]
    advice = weather_advice(first_day)
    weather_lines = [
        f"Weather for {destination}:",
        f"- {first_day.date}: {first_day.condition}, {first_day.temp_high}°C / {first_day.temp_low}°C, {first_day.description}",
        f"- Travel guidance: {advice}",
    ]

    if any(condition in first_day.condition.lower() for condition in ["rain", "storm", "snow"]):
        weather_lines.append("- Weather outlook: not ideal for outdoor-heavy sightseeing; suggest indoor or flexible plans.")
    else:
        weather_lines.append("- Weather outlook: generally suitable for travel and sightseeing.")

    return "\n".join(weather_lines)


def fetch_places(destination: str):
    """Fetch attractions, restaurants, and hotels once for a request."""
    attractions = get_top_attractions(destination, max_results=3)
    restaurants = get_top_restaurants(destination, max_results=3)
    hotels = get_hotels(destination, max_results=3)
    return attractions, restaurants, hotels


def build_places_context(destination: str, attractions, restaurants, hotels) -> str:
    """Build a short places summary for prompt context."""
    source = "Google Maps" if settings.has_google_maps else "OpenStreetMap"
    if not attractions and not restaurants and not hotels:
        return f"{source} places data for {destination} is unavailable right now."

    context_lines = [f"Places for {destination} (via {source}):"]

    if attractions:
        context_lines.append("- Top attractions:")
        for place in attractions:
            rating_text = f", rating {place.rating}" if place.rating is not None else ""
            price_text = f", price level {place.price_level}" if place.price_level is not None else ""
            open_text = f", open now: {place.open_now}" if place.open_now is not None else ""
            context_lines.append(f"  - {place.name} ({place.address}{rating_text}{price_text}{open_text})")

    if restaurants:
        context_lines.append("- Recommended restaurants:")
        for place in restaurants:
            rating_text = f", rating {place.rating}" if place.rating is not None else ""
            price_text = f", price level {place.price_level}" if place.price_level is not None else ""
            open_text = f", open now: {place.open_now}" if place.open_now is not None else ""
            context_lines.append(f"  - {place.name} ({place.address}{rating_text}{price_text}{open_text})")

    if hotels:
        context_lines.append("- Suggested hotels:")
        for place in hotels:
            rating_text = f", rating {place.rating}" if place.rating is not None else ""
            price_text = f", price level {place.price_level}" if place.price_level is not None else ""
            open_text = f", open now: {place.open_now}" if place.open_now is not None else ""
            context_lines.append(f"  - {place.name} ({place.address}{rating_text}{price_text}{open_text})")

    context_lines.append(f"- {source} links:")
    for place in attractions + restaurants + hotels:
        context_lines.append(f"  - {place.name}: {maps_link_for_place(place)}")

    return "\n".join(context_lines)


def maps_link_for_place(place) -> str:
    """Create a map link for a place — Google Maps if the key is set, else OSM."""
    if settings.has_google_maps:
        return get_gmaps_link(place)

    # OpenStreetMap fallback
    if place.lat is not None and place.lon is not None:
        return f"https://www.openstreetmap.org/?mlat={place.lat}&mlon={place.lon}#map=16/{place.lat}/{place.lon}"

    query = place.address or place.name
    return f"https://www.openstreetmap.org/search?query={query.replace(' ', '+')}"


def build_maps_section(destination: str, attractions, restaurants, hotels) -> str:
    """Build a short, user-facing maps section for the reply."""
    use_gmaps = settings.has_google_maps
    source = "Google Maps" if use_gmaps else "OpenStreetMap"
    places = attractions + restaurants + hotels
    if not places:
        if use_gmaps:
            encoded = destination.replace(" ", "+")
            return "\n".join([
                f"{source} references:",
                f"- Attractions: https://www.google.com/maps/search/{encoded}+attractions",
                f"- Restaurants: https://www.google.com/maps/search/{encoded}+restaurants",
                f"- Hotels: https://www.google.com/maps/search/{encoded}+hotels",
            ])
        else:
            encoded = destination.replace(" ", "+")
            return "\n".join([
                f"{source} references:",
                f"- Attractions: https://www.openstreetmap.org/search?query={encoded}+attractions",
                f"- Restaurants: https://www.openstreetmap.org/search?query={encoded}+restaurants",
                f"- Hotels: https://www.openstreetmap.org/search?query={encoded}+hotels",
            ])

    lines = [f"{source} references:"]
    for place in places:
        lines.append(f"- {place.name}: {maps_link_for_place(place)}")
    return "\n".join(lines)

# ──────────────────────────────────────────
#  API ENDPOINTS
# ──────────────────────────────────────────


@app.get("/")
def root():
    """Health check - confirms the server is running."""
    return {"status": "ok", "app": "AI Travel Planner"}


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    """
    Send a message to the AI travel planner.
    Returns a Server-Sent Events stream so the frontend can render as text arrives.
    
    Expects:  {"message": "Plan a trip to Paris", "history": [...]}
    Streams:  data: {"chunk":"...text..."}
              data: {"maps":"OpenStreetMap references:..."}
              data: {"done":true}
    """
    if not GROQ_API_KEY:
        async def err_stream():
            yield f"data: {json.dumps({'chunk': '⚠️ Groq API key is not set. Please add GROQ_API_KEY to your .env file.'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    try:
        print(f"[chat] request received: {request.message}")
        destination = extract_destination(request.message)
        print(f"[chat] extracted destination: {destination}")

        # Fetch weather & places (sync, happens before streaming starts)
        weather_context = build_weather_context(destination) if destination else ""
        attractions = restaurants = hotels = []
        if destination:
            attractions, restaurants, hotels = fetch_places(destination)
        places_context = build_places_context(destination, attractions, restaurants, hotels) if destination else ""
        maps_section = build_maps_section(destination, attractions[:2], restaurants[:2], hotels[:2]) if destination else ""
        print(f"[chat] weather={bool(weather_context)} places={bool(places_context)} maps={bool(maps_section)}")

        # Build the conversation for Groq
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if weather_context:
            messages.append({
                "role": "system",
                "content": f"Use this weather context when planning trips:\n{weather_context}",
            })

        if places_context:
            source = "Google Maps" if settings.has_google_maps else "OpenStreetMap"
            messages.append({
                "role": "system",
                "content": f"Use this {source} context when planning trips:\n{places_context}",
            })

        # Add conversation history (last 10 messages)
        for msg in request.history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        messages.append({"role": "user", "content": request.message})

    except Exception as e:
        print(f"[chat] prep error: {e}")
        async def err_stream():
            yield f"data: {json.dumps({'chunk': f'❌ Preparation error: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    # ─── STREAM GENERATOR ─────────────────────────────────
    async def generate():
        try:
            client = AsyncGroq(api_key=GROQ_API_KEY)
            stream = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield f"data: {json.dumps({'chunk': delta.content})}\n\n"

            # Append maps section after the AI response
            if maps_section:
                yield f"data: {json.dumps({'maps': maps_section})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"
            print("[chat] stream complete")

        except Exception as e:
            print(f"[chat] stream error: {e}")
            yield f"data: {json.dumps({'chunk': f'❌ Error: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ──────────────────────────────────────────
#  SPA CATCH-ALL (must be last route)
# ──────────────────────────────────────────
if os.path.isdir(FRONTEND_DIR):
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React app for any non-API path."""
        file_path = os.path.join(FRONTEND_DIR, "index.html")
        return FileResponse(file_path, media_type="text/html")
