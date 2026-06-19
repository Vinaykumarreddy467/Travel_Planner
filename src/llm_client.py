"""Groq LLM client for the Travel Planner."""

import json
from groq import Groq
from .config import settings


SYSTEM_PROMPT = """You are an expert travel planner AI. Your job is to create detailed, 
realistic day-by-day travel itineraries based on user preferences.

Given a user's travel request, respond with a valid JSON object (no markdown, no code fences).

The JSON must follow this structure exactly:
{
  "trip_name": "string - catchy trip name",
  "destination": "string",
  "duration_days": integer,
  "budget": float,
  "days": [
    {
      "day": integer,
      "theme": "string - theme for this day (e.g. 'Arrival & Street Food', 'Cultural Exploration')",
      "activities": [
        {
          "time_slot": "morning" | "afternoon" | "evening",
          "activity": "string describing the activity",
          "estimated_cost": float,
          "notes": "string - tips or advice"
        }
      ],
      "total_day_cost": float
    }
  ],
  "tips": ["string - general travel tips"],
  "total_estimated_cost": float
}

Rules:
- Be realistic with pricing (meals: $10-30, attractions: $0-50, transport: $5-50)
- Mix popular attractions with hidden gems
- Balance busy days with relaxed ones
- Consider meal times and travel time between locations
- Include a mix of free and paid activities
- Keep descriptions concise but informative
"""


def generate_plan(
    destination: str,
    days: int,
    budget: float = 0,
    preferences: str = "",
) -> dict:
    """
    Generate a travel plan using Groq LLM.
    
    Args:
        destination: City/country name
        days: Number of days
        budget: Total budget in USD
        preferences: User preferences (e.g. "foodie, culture, family")
    
    Returns:
        Dict with the travel plan JSON
    """
    if not settings.has_groq:
        print("⚠️  Groq API key not set. Set GROQ_API_KEY in .env")
        return _fallback_plan(destination, days)

    budget_str = f"${budget:,.0f}" if budget > 0 else "No specific budget"

    user_prompt = f"""Plan a {days}-day trip to {destination}.
Budget: {budget_str}
Preferences: {preferences or 'No specific preferences - mix of culture, food, and sightseeing'}

Create a detailed day-by-day itinerary with realistic costs in USD.
"""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if content:
            return json.loads(content)

    except Exception as e:
        print(f"❌ Groq LLM call failed: {e}")
        print("ℹ️  Falling back to template-based plan...")

    return _fallback_plan(destination, days)


def _fallback_plan(destination: str, days: int) -> dict:
    """Generate a simple template-based plan when the LLM is unavailable."""
    plan = {
        "trip_name": f"Trip to {destination}",
        "destination": destination,
        "duration_days": days,
        "budget": 0,
        "total_estimated_cost": days * 150,
        "days": [],
        "tips": [
            f"Book accommodation in {destination} in advance",
            "Check local transportation options",
            "Pack appropriate clothing for the season",
        ],
    }

    themes = ["Arrival & Exploration", "Cultural Day", "Nature & Relaxation", "Adventure", "Shopping & Local Life", "Food & Markets", "Free Day"]
    for i in range(days):
        day_plan = {
            "day": i + 1,
            "theme": themes[i % len(themes)],
            "activities": [
                {
                    "time_slot": "morning",
                    "activity": f"Explore {destination} morning attractions",
                    "estimated_cost": 20,
                    "notes": "Start early to beat the crowds",
                },
                {
                    "time_slot": "afternoon",
                    "activity": "Lunch at a local restaurant and sightseeing",
                    "estimated_cost": 35,
                    "notes": "Try the local cuisine",
                },
                {
                    "time_slot": "evening",
                    "activity": "Dinner and evening walk",
                    "estimated_cost": 45,
                    "notes": "Check out local nightlife",
                },
            ],
            "total_day_cost": 100,
        }
        plan["days"].append(day_plan)

    return plan
