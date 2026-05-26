"""
Google Places API client.
Finds local businesses by location and optional category filter.
Uses Places API (New) - the modern endpoint, not the legacy one.
"""
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse
from src.config import GOOGLE_PLACES_API_KEY

PLACES_API_BASE = "https://places.googleapis.com/v1"


def search_nearby(
    latitude: float,
    longitude: float,
    radius_meters: int = 5000,
    included_types: Optional[List[str]] = None,
    max_results: int = 20,
) -> List[Dict]:
    """
    Search for businesses near a location.

    Args:
        latitude: Center point latitude
        longitude: Center point longitude
        radius_meters: Search radius (max 50000 per API)
        included_types: Place types to include (None = all types)
        max_results: Max results (API hard cap is 20 per call)

    Returns:
        List of dicts with keys: place_id, name, address, website, types
        Only returns OPERATIONAL businesses that have a website.
    """
    url = f"{PLACES_API_BASE}/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.websiteUri,places.types,places.businessStatus"
        ),
    }
    body = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
        "maxResultCount": min(max_results, 20),
    }
    if included_types:
        body["includedTypes"] = included_types

    response = requests.post(url, json=body, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    places = data.get("places", [])

    results = []
    for place in places:
        if place.get("businessStatus") != "OPERATIONAL":
            continue
        if not place.get("websiteUri"):
            continue
        results.append({
            "place_id": place.get("id"),
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "website": place.get("websiteUri", ""),
            "types": place.get("types", []),
        })
    return results


def extract_domain(website_url: str) -> Optional[str]:
    """
    Extract clean domain from a website URL.
    Example: https://www.foo.com/page -> foo.com
    """
    try:
        parsed = urlparse(website_url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


if __name__ == "__main__":
    # Smoke test: search near Deerfield, IL
    print("Testing Places API near Deerfield, IL...")
    results = search_nearby(
        latitude=42.1711,
        longitude=-87.8445,
        radius_meters=3000,
        max_results=10,
    )
    print(f"Found {len(results)} businesses with websites")
    for r in results[:3]:
        print(f"  - {r['name']} | {extract_domain(r['website'])}")
