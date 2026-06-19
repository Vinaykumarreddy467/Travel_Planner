"""
Google Maps Places API (New) integration for the Travel Planner.

Uses the Places API (New) — `searchText` and `searchNearby` endpoints.
https://developers.google.com/maps/documentation/places/web-service/overview

Requires GOOGLE_MAPS_API_KEY in .env
"""

import requests
from .config import settings
from .models import Place

PLACES_API_BASE = "https://places.googleapis.com/v1/places"

# Default field mask — only request what we need
FIELD_MASK = (
    "places.displayName,"
    "places.formattedAddress,"
    "places.rating,"
    "places.priceLevel,"
    "places.location,"
    "places.primaryType,"
    "places.currentOpeningHours,"
    "places.googleMapsUri"
)

TIMEOUT = 10


# ─── PRICE LEVEL MAPPING ───────────────────────────────
# Google returns: PRICE_LEVEL_UNSPECIFIED, PRICE_LEVEL_FREE, PRICE_LEVEL_INEXPENSIVE,
#                 PRICE_LEVEL_MODERATE, PRICE_LEVEL_EXPENSIVE, PRICE_LEVEL_VERY_EXPENSIVE
_PRICE_MAP = {
    "PRICE_LEVEL_UNSPECIFIED": None,
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


def _parse_place(raw: dict) -> Place:
    """Convert a raw Google Places API response dict into our Place model."""
    display_name = raw.get("displayName", {})
    name = display_name.get("text", "Unknown") if isinstance(display_name, dict) else str(display_name)

    location = raw.get("location", {}) or {}
    lat = location.get("latitude")
    lon = location.get("longitude")

    price_str = raw.get("priceLevel", "")
    price_level = _PRICE_MAP.get(price_str)

    hours = raw.get("currentOpeningHours", {}) or {}
    open_now = hours.get("openNow")

    return Place(
        name=name,
        address=raw.get("formattedAddress", ""),
        rating=raw.get("rating"),
        price_level=price_level,
        place_type=raw.get("primaryType", "place"),
        lat=float(lat) if lat is not None else None,
        lon=float(lon) if lon is not None else None,
        open_now=open_now,
    )


def _places_api_request(endpoint: str, body: dict) -> list[dict] | None:
    """Make a POST to a Google Places API endpoint and return the places array."""
    if not settings.has_google_maps:
        print("[google_maps] no API key configured")
        return None

    url = f"{PLACES_API_BASE}{endpoint}"
    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
        "Content-Type": "application/json",
    }

    try:
        print(f"[google_maps] POST {url}")
        resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        places = data.get("places", [])
        print(f"[google_maps] got {len(places)} results")
        return places
    except requests.exceptions.HTTPError as e:
        print(f"[google_maps] HTTP error: {e.response.status_code} {e.response.text[:300]}")
        return None
    except Exception as e:
        print(f"[google_maps] request failed: {e}")
        return None


# ─── PUBLIC API ─────────────────────────────────────────


def search_text(query: str, max_results: int = 5, language: str = "en") -> list[Place]:
    """
    Search for places using the Places API (New) Text Search.

    Args:
        query: Free-form text query (e.g. "restaurants in Paris", "museums in Tokyo")
        max_results: How many results to return (max 20)
        language: Preferred language code (e.g. "en", "ja", "fr")

    Returns:
        List of Place objects
    """
    raw = _places_api_request("/:searchText", {
        "textQuery": query,
        "maxResultCount": min(max_results, 20),
        "languageCode": language,
    })

    if raw is None:
        return []

    return [_parse_place(p) for p in raw]


def search_nearby(
    lat: float,
    lon: float,
    place_type: str = "tourist_attraction",
    radius: int = 5000,
    max_results: int = 5,
) -> list[Place]:
    """
    Search for places near a coordinate using the Places API (New) Nearby Search.

    Args:
        lat: Latitude
        lon: Longitude
        place_type: Type filter (e.g. "restaurant", "hotel", "tourist_attraction", "museum")
        radius: Search radius in meters
        max_results: How many results to return (max 20)

    Returns:
        List of Place objects
    """
    # Google's type list: https://developers.google.com/maps/documentation/places/web-service/place-types
    raw = _places_api_request("/:searchNearby", {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": radius,
            }
        },
        "includedTypes": [place_type],
        "maxResultCount": min(max_results, 20),
    })

    if raw is None:
        return []

    return [_parse_place(p) for p in raw]


def get_place_link(place: Place) -> str:
    """Generate a Google Maps link for a place."""
    if place.lat is not None and place.lon is not None:
        # Deep link to the location
        return f"https://www.google.com/maps/search/?api=1&query={place.lat},{place.lon}"
    # Fall back to search by name
    return f"https://www.google.com/maps/search/{place.name.replace(' ', '+')}"


def get_top_attractions(city: str, max_results: int = 5) -> list[Place]:
    """Get top tourist attractions in a city via Google Maps."""
    return search_text(f"top tourist attractions in {city}", max_results)


def get_top_restaurants(city: str, max_results: int = 5) -> list[Place]:
    """Get top restaurants in a city via Google Maps."""
    return search_text(f"best restaurants in {city}", max_results)


def get_hotels(city: str, max_results: int = 5) -> list[Place]:
    """Get hotels in a city via Google Maps."""
    return search_text(f"hotels in {city}", max_results)


def get_museums(city: str, max_results: int = 3) -> list[Place]:
    """Get museums in a city via Google Maps."""
    return search_text(f"museums in {city}", max_results)
