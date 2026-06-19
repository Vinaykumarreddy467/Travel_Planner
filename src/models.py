"""Pydantic data models for the Travel Planner."""

from pydantic import BaseModel
from typing import Optional


class Coordinates(BaseModel):
    lat: float
    lon: float


class Weather(BaseModel):
    date: str
    temp_high: float
    temp_low: float
    condition: str  # e.g. "Sunny", "Rain", "Clouds"
    icon: str      # e.g. "01d"
    description: str


class Place(BaseModel):
    name: str
    address: str
    rating: Optional[float] = None
    price_level: Optional[int] = None  # 0=free, 1=cheap, 2=moderate, 3=expensive, 4=very expensive
    place_type: str  # "restaurant", "attraction", "hotel", "museum", etc.
    lat: Optional[float] = None
    lon: Optional[float] = None
    open_now: Optional[bool] = None


class Activity(BaseModel):
    time_slot: str          # "morning", "afternoon", "evening"
    activity: str
    place: Optional[Place] = None
    estimated_cost: float = 0
    notes: str = ""


class DayPlan(BaseModel):
    day: int
    date: str
    theme: str
    weather: Optional[Weather] = None
    activities: list[Activity] = []
    total_day_cost: float = 0


class TravelPlan(BaseModel):
    trip_name: str
    destination: str
    destination_coords: Optional[Coordinates] = None
    duration_days: int
    budget: float = 0
    total_estimated_cost: float = 0
    days: list[DayPlan] = []
    tips: list[str] = []


class UserQuery(BaseModel):
    destination: str
    duration_days: int
    budget: float = 0
    preferences: str = ""  # e.g. "foodie, culture, family-friendly, budget"
