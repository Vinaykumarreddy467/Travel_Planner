"""Configuration and API key management for the Travel Planner."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Load API keys from environment variables."""

    # Groq API for LLM (free tier: 14,400 req/day)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # OpenWeatherMap (free tier: 1,000,000 calls/month)
    OWM_API_KEY: str = os.getenv("OWM_API_KEY", "")

    # Google Maps (free tier: $200/month credit)
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_owm(self) -> bool:
        return bool(self.OWM_API_KEY)

    @property
    def has_google_maps(self) -> bool:
        return bool(self.GOOGLE_MAPS_API_KEY)

    @property
    def is_ready(self) -> bool:
        """All three APIs are required for full functionality."""
        return self.has_groq and self.has_owm and self.has_google_maps


settings = Settings()
