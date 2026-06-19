"""
Places lookup for the Travel Planner.

Tries Google Maps Places API (New) first when the API key is configured.
Falls back to OpenStreetMap (Nominatim + Overpass) otherwise.
"""

import requests
from .config import settings
from .models import Place, Coordinates
from .google_maps import (  # noqa: F811 — re-exported for convenience
    search_text as _gmaps_search_text,
    search_nearby as _gmaps_search_nearby,
    get_place_link as get_gmaps_link,
)


NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
]
USER_AGENT = "travel-planner-demo/1.0"


def _search_nominatim_places(query: str, max_results: int) -> list[Place]:
    """Fallback place search using Nominatim text search results."""
    print(f"[places] nominatim fallback search: {query}")
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": max_results,
    }

    try:
        resp = requests.get(NOMINATIM_BASE, params=params, timeout=10, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[places] nominatim fallback failed: {e}")
        return []

    places: list[Place] = []
    for item in data[:max_results]:
        display_name = item.get("display_name", "Unknown")
        places.append(Place(
            name=display_name.split(",")[0],
            address=display_name,
            rating=None,
            price_level=None,
            place_type="search_result",
            lat=float(item["lat"]) if item.get("lat") else None,
            lon=float(item["lon"]) if item.get("lon") else None,
        ))

    print(f"[places] nominatim fallback returned {len(places)} place(s)")
    return places


def geocode_location(location: str) -> Coordinates | None:
    """Convert a city or place name into coordinates using OpenStreetMap Nominatim."""

    print(f"[places] geocoding location: {location}")

    params = {
        "q": location,
        "format": "jsonv2",
        "limit": 1,
    }

    try:
        resp = requests.get(NOMINATIM_BASE, params=params, timeout=10, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        if not data:
            print(f"[places] geocoding returned no results for: {location}")
            return None

        lat = data[0].get("lat")
        lon = data[0].get("lon")
        if lat is None or lon is None:
            return None

        coords = Coordinates(lat=float(lat), lon=float(lon))
        print(f"[places] geocoding success: {location} -> {coords.lat}, {coords.lon}")
        return coords
    except Exception as e:
        print(f"❌ Geocoding failed for '{location}': {e}")
        return None


def _query_overpass(location: Coordinates, place_type: str, radius: int) -> list[dict]:
    """Query Overpass for nearby places around a coordinate."""
    print(f"[places] overpass search: type={place_type}, radius={radius}, location={location.lat},{location.lon}")
    filters = {
        "tourist_attraction": 'tourism="attraction"',
        "restaurant": 'amenity="restaurant"',
        "lodging": 'tourism~"hotel|hostel|guest_house|motel"',
        "museum": 'tourism="museum"',
    }

    place_filter = filters.get(place_type, 'tourism="attraction"')
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{radius},{location.lat},{location.lon})[{place_filter}];
      way(around:{radius},{location.lat},{location.lon})[{place_filter}];
      relation(around:{radius},{location.lat},{location.lon})[{place_filter}];
    );
    out center tags;
    """

    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"[places] trying overpass endpoint: {endpoint}")
            resp = requests.get(endpoint, params={"data": query}, timeout=5, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            data = resp.json()
            print(f"[places] overpass returned {len(data.get('elements', []))} element(s) from {endpoint}")
            return data.get("elements", [])
        except Exception as e:
            last_error = e
            print(f"[places] overpass endpoint failed: {endpoint} -> {e}")

    if last_error:
        raise last_error

    return []


def _element_to_place(element: dict, place_type: str) -> Place:
    """Convert an Overpass element into a Place model."""
    tags = element.get("tags", {})
    center = element.get("center", {})
    lat = element.get("lat", center.get("lat"))
    lon = element.get("lon", center.get("lon"))

    name = tags.get("name") or tags.get("brand") or "Unknown"
    address_parts = [part for part in [tags.get("addr:street"), tags.get("addr:housenumber"), tags.get("addr:city")] if part]
    address = ", ".join(address_parts) if address_parts else tags.get("description", "")

    return Place(
        name=name,
        address=address,
        rating=None,
        price_level=None,
        place_type=place_type,
        lat=float(lat) if lat is not None else None,
        lon=float(lon) if lon is not None else None,
    )


def search_places(
    query: str,
    location: str | Coordinates,
    place_type: str = "tourist_attraction",
    radius: int = 5000,
    max_results: int = 5,
) -> list[Place]:
    """
    Search for places — tries Google Maps first (if key configured).
    If Google Maps returns empty or fails, falls back to OpenStreetMap.

    Args:
        query: What to search for (e.g. "best restaurants in Paris")
        location: City name or Coordinates
        place_type: Type filter (tourist_attraction, restaurant, museum, etc.)
        radius: Search radius in meters (only used for OSM Overpass)
        max_results: Max places to return

    Returns:
        List of Place objects
    """
    results: list[Place] = []

    # ── 1) Google Maps ───────────────────────────────────
    if settings.has_google_maps:
        results = _search_with_gmaps(query, location, place_type, max_results)
        if results:
            print(f"[places] gmaps returned {len(results)} result(s) — using these")
            return results
        print("[places] gmaps returned empty — falling back to OpenStreetMap")

    # ── 2) OSM fallback ──────────────────────────────────
    results = _search_with_osm(query, location, place_type, radius, max_results)
    if results:
        print(f"[places] osm returned {len(results)} result(s)")
    else:
        print("[places] osm also returned empty — no places found")
    return results


def _search_with_gmaps(
    query: str,
    location: str | Coordinates,
    place_type: str,
    max_results: int,
) -> list[Place]:
    """Search using Google Maps Places API (New)."""
    if isinstance(location, str):
        # Build a text query — use friendlier labels for known defaults
        _type_labels = {
            "tourist_attraction": "tourist attractions",
            "restaurant": "restaurants",
            "lodging": "hotels",
            "museum": "museums",
        }

        known_defaults = {"", "top attractions", "best rated restaurants", "hotels", "museums"}
        if query in known_defaults:
            type_label = _type_labels.get(place_type, place_type.replace("_", " "))
            text_query = f"best {type_label} in {location}"
        else:
            text_query = f"{query} in {location}"

        print(f"[places] gmaps text search: {text_query}")
        return _gmaps_search_text(text_query, max_results)
    else:
        gmaps_type = _osm_to_gmaps_type(place_type)
        print(f"[places] gmaps nearby search: type={gmaps_type} at {location.lat},{location.lon}")
        return _gmaps_search_nearby(location.lat, location.lon, gmaps_type, max_results=max_results)


def _search_with_osm(
    query: str,
    location: str | Coordinates,
    place_type: str,
    radius: int,
    max_results: int,
) -> list[Place]:
    """Search using OpenStreetMap (Nominatim + Overpass)."""
    if isinstance(location, str):
        coords = geocode_location(location)
        if not coords:
            print(f"⚠️  OSM geocoding failed for '{location}'")
            return _search_nominatim_places(f"{query} in {location}", max_results)
    else:
        coords = location

    print(f"[places] osm search: query={query}, type={place_type}, location={coords}")

    try:
        elements = _query_overpass(coords, place_type, radius)
    except Exception as e:
        print(f"❌ Places search failed: {e}")
        query_text = f"{query} in {location}" if isinstance(location, str) else query
        return _search_nominatim_places(query_text, max_results)

    places = []
    for element in elements[:max_results]:
        places.append(_element_to_place(element, place_type))

    return places


def _osm_to_gmaps_type(place_type: str) -> str:
    """Map OSM place type labels to Google Maps place types."""
    mapping = {
        "tourist_attraction": "tourist_attraction",
        "restaurant": "restaurant",
        "lodging": "hotel",
        "museum": "museum",
    }
    return mapping.get(place_type, place_type)


# ─── CONVENIENCE FUNCTIONS ──────────────────────────────
# All route through search_places() which handles GMaps → OSM fallback

def get_top_attractions(city: str, max_results: int = 5) -> list[Place]:
    """Get top tourist attractions in a city."""
    return search_places("top attractions", city, "tourist_attraction", max_results=max_results)


def get_top_restaurants(city: str, max_results: int = 5) -> list[Place]:
    """Get top-rated restaurants in a city."""
    return search_places("best rated restaurants", city, "restaurant", max_results=max_results)


def get_hotels(city: str, max_results: int = 5) -> list[Place]:
    """Get hotels in a city."""
    return search_places("hotels", city, "lodging", max_results=max_results)


def get_museums(city: str, max_results: int = 3) -> list[Place]:
    """Get museums in a city."""
    return search_places("museums", city, "museum", max_results=max_results)
