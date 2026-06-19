"""Main Travel Planner orchestrator - ties together LLM, weather, and places."""

import json
from datetime import datetime, timedelta
from .config import settings
from .models import TravelPlan, DayPlan, Activity, Weather, Place
from .llm_client import generate_plan
from .weather import get_forecast, get_coordinates, weather_emoji, weather_advice
from .places import get_top_attractions, get_top_restaurants


class TravelPlanner:
    """
    AI Travel Planner that combines:
    - Groq LLM for itinerary generation
    - OpenWeatherMap for weather forecasts
    - Google Places API for real places data
    """

    def __init__(self):
        self.llm_available = settings.has_groq
        self.weather_available = settings.has_owm
        self.places_available = settings.has_google_maps

    def check_ready(self) -> list[str]:
        """Check which APIs are configured. Returns list of missing keys."""
        missing = []
        if not settings.has_groq:
            missing.append("GROQ_API_KEY")
        if not settings.has_owm:
            missing.append("OWM_API_KEY")
        if not settings.has_google_maps:
            missing.append("GOOGLE_MAPS_API_KEY")
        return missing

    def plan_trip(
        self,
        destination: str,
        days: int,
        budget: float = 0,
        preferences: str = "",
    ) -> TravelPlan:
        """
        Create a complete travel plan.
        
        1. Generate itinerary with Groq LLM
        2. Enrich with real weather data
        3. Enrich with real places from Google Maps
        
        Returns:
            TravelPlan object
        """
        print(f"\n{'='*50}")
        print(f"🧳 PLANNING YOUR TRIP TO {destination.upper()}")
        print(f"{'='*50}\n")

        # Step 1: Generate base plan with LLM
        print("🤖 Step 1/3: Generating itinerary with AI...")
        raw_plan = generate_plan(destination, days, budget, preferences)
        print(f"   ✅ {raw_plan.get('trip_name', 'Trip planned!')}\n")

        # Step 2: Get weather
        print("🌤️  Step 2/3: Fetching weather forecast...")
        weather_data = get_forecast(destination, days=days)
        if weather_data:
            print(f"   ✅ Weather data for {len(weather_data)} days loaded\n")
        else:
            print("   ⚠️  Weather data unavailable (set OWM_API_KEY)\n")

        # Step 3: Get places
        print("📍 Step 3/3: Finding real attractions & restaurants...")
        attractions = []
        restaurants = []
        if settings.has_google_maps:
            attractions = get_top_attractions(destination, max_results=5)
            restaurants = get_top_restaurants(destination, max_results=5)
            print(f"   ✅ {len(attractions)} attractions + {len(restaurants)} restaurants found\n")
        else:
            print("   ⚠️  Places data unavailable (set GOOGLE_MAPS_API_KEY)\n")

        # Build the TravelPlan model
        coords = get_coordinates(destination) if settings.has_owm else None

        plan = TravelPlan(
            trip_name=raw_plan.get("trip_name", f"Trip to {destination}"),
            destination=destination,
            destination_coords=coords,
            duration_days=days,
            budget=budget,
            total_estimated_cost=raw_plan.get("total_estimated_cost", days * 150),
            tips=raw_plan.get("tips", []),
        )

        # Build day-by-day plans
        start_date = datetime.now()
        for i, day_data in enumerate(raw_plan.get("days", [])):
            day_num = i + 1
            date = (start_date + timedelta(days=day_num)).strftime("%Y-%m-%d")

            # Match weather for this day
            day_weather = None
            if weather_data and i < len(weather_data):
                day_weather = weather_data[i]

            # Build activities
            activities = []
            for act in day_data.get("activities", []):
                activities.append(Activity(
                    time_slot=act.get("time_slot", "morning"),
                    activity=act.get("activity", ""),
                    estimated_cost=act.get("estimated_cost", 0),
                    notes=act.get("notes", ""),
                ))

            # Add place recommendations
            if attractions and day_num == 1:
                # Suggest top attractions on day 1
                pass  # Could add enrichment here

            plan.days.append(DayPlan(
                day=day_num,
                date=date,
                theme=day_data.get("theme", "Explore"),
                weather=day_weather,
                activities=activities,
                total_day_cost=day_data.get("total_day_cost", 0),
            ))

        return plan

    def print_itinerary(self, plan: TravelPlan) -> None:
        """Print a beautiful, formatted itinerary to the console."""
        print("\n" + "="*60)
        print(f"  🧳 {plan.trip_name.upper()}")
        print("="*60)
        print(f"  📍 Destination: {plan.destination}")
        print(f"  📅 Duration:    {plan.duration_days} days")
        if plan.budget > 0:
            print(f"  💰 Budget:      ${plan.budget:,.0f}")
        print(f"  💵 Est. Total:  ${plan.total_estimated_cost:,.0f}")
        print("="*60)

        for day in plan.days:
            print(f"\n{'─'*50}")
            weather_str = ""
            if day.weather:
                emoji = weather_emoji(day.weather.condition)
                weather_str = f"  {emoji} {day.weather.temp_high}°C / {day.weather.temp_low}°C - {day.weather.description}"

            print(f"  📆 Day {day.day} — {day.date}  {weather_str}")
            print(f"  🎯 Theme: {day.theme}")
            print(f"{'─'*50}")

            for act in day.activities:
                slot_icon = {"morning": "🌅", "afternoon": "☀️", "evening": "🌙"}
                icon = slot_icon.get(act.time_slot, "⏰")
                cost_str = f"${act.estimated_cost:.0f}" if act.estimated_cost > 0 else "Free"
                print(f"    {icon} [{act.time_slot.upper()}] {act.activity}")
                print(f"       💵 {cost_str}")
                if act.notes:
                    print(f"       💡 {act.notes}")

            print(f"  💰 Day total: ${day.total_day_cost:.0f}")

        if plan.tips:
            print(f"\n{'─'*50}")
            print("  💡 TRAVEL TIPS")
            print(f"{'─'*50}")
            for tip in plan.tips:
                print(f"    • {tip}")

        if plan.destination_coords:
            print(f"\n{'─'*50}")
            print(f"  🗺️  Coords: {plan.destination_coords.lat}, {plan.destination_coords.lon}")
            maps_url = f"https://www.google.com/maps/@{plan.destination_coords.lat},{plan.destination_coords.lon},12z"
            print(f"  🔗  {maps_url}")

        print(f"\n{'='*60}")
        print(f"  ✨ Happy travels! ✨")
        print(f"{'='*60}\n")

    def save_itinerary(self, plan: TravelPlan, filepath: str = "output/itinerary.json") -> str:
        """Save the itinerary as a JSON file."""
        import os
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(plan.model_dump(), f, indent=2, default=str)

        return filepath
