"""
Discover potential buyers using Google Places API (New) Text Search.

Usage:
    python tools/discover_google_places.py

Reads search queries from workflows/discover_leads.md config.
Outputs raw leads to .tmp/raw_leads_places.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", ".tmp", "raw_leads_places.json")

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
    "places.priceLevel",
    "places.types",
    "places.nationalPhoneNumber",
    "nextPageToken",
])

# Search configurations per buyer profile
SEARCHES = {
    "wedding_venues": {
        "queries": ["wedding venue", "wedding reception venue", "event venue weddings"],
        "cities": [
            "New York, NY", "Boston, MA", "Philadelphia, PA", "Washington, DC",
            "Nashville, TN", "Chicago, IL", "Miami, FL", "Los Angeles, CA",
            "San Francisco, CA", "Denver, CO", "Seattle, WA",
            "Charleston, SC", "Savannah, GA", "Austin, TX", "Dallas, TX",
        ],
    },
    "floral_designers": {
        "queries": ["wedding florist", "event florist", "floral designer"],
        "cities": [
            "New York, NY", "Boston, MA", "Philadelphia, PA", "Washington, DC",
            "Nashville, TN", "Chicago, IL", "Miami, FL", "Los Angeles, CA",
            "San Francisco, CA", "Denver, CO", "Seattle, WA",
        ],
    },
}

# How many pages to fetch per query+city combo (max 3, each page = 20 results)
MAX_PAGES = 2


def search_places(query: str, city: str, max_pages: int = MAX_PAGES) -> list[dict]:
    """Run a text search and return all results across pages."""
    results = []
    page_token = None

    for page in range(max_pages):
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": FIELD_MASK,
        }

        body = {
            "textQuery": f"{query} in {city}",
            "pageSize": 20,
        }
        if page_token:
            body["pageToken"] = page_token

        resp = requests.post(ENDPOINT, headers=headers, json=body)

        if resp.status_code != 200:
            print(f"  ERROR [{resp.status_code}]: {query} in {city} (page {page+1})")
            print(f"  {resp.text[:200]}")
            break

        data = resp.json()
        places = data.get("places", [])
        results.extend(places)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        # Small delay between pages to be polite
        time.sleep(0.5)

    return results


def normalize_place(place: dict, profile: str, query: str, city: str) -> dict:
    """Flatten a Places API response into a clean lead record."""
    return {
        "source": "google_places",
        "buyer_profile": profile,
        "search_query": query,
        "search_city": city,
        "place_id": place.get("id", ""),
        "name": place.get("displayName", {}).get("text", ""),
        "address": place.get("formattedAddress", ""),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "website": place.get("websiteUri", ""),
        "price_level": place.get("priceLevel", ""),
        "phone": place.get("nationalPhoneNumber", ""),
        "types": place.get("types", []),
    }


def run(profiles: Optional[list] = None, cities_override: Optional[list] = None):
    """
    Run discovery for specified profiles (or all).

    Args:
        profiles: List of profile keys to search (default: all)
        cities_override: If provided, search only these cities (for testing)
    """
    if not API_KEY:
        print("ERROR: GOOGLE_PLACES_API_KEY not set in .env")
        sys.exit(1)

    all_leads = []
    search_count = 0

    target_profiles = profiles or list(SEARCHES.keys())

    for profile in target_profiles:
        config = SEARCHES.get(profile)
        if not config:
            print(f"WARNING: Unknown profile '{profile}', skipping")
            continue

        cities = cities_override or config["cities"]
        queries = config["queries"]

        print(f"\n{'='*60}")
        print(f"Profile: {profile} ({len(queries)} queries x {len(cities)} cities)")
        print(f"{'='*60}")

        for query in queries:
            for city in cities:
                search_count += 1
                print(f"  [{search_count}] \"{query}\" in {city}...", end=" ", flush=True)
                places = search_places(query, city)
                print(f"{len(places)} results")

                for place in places:
                    lead = normalize_place(place, profile, query, city)
                    all_leads.append(lead)

                # Rate limit: small delay between searches
                time.sleep(0.3)

    # Merge with existing data from prior runs (so we don't overwrite)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing_leads = json.load(f)
        all_leads = existing_leads + all_leads

    # Deduplicate by place_id
    seen_ids = set()
    unique_leads = []
    for lead in all_leads:
        pid = lead["place_id"]
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            unique_leads.append(lead)

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(unique_leads, f, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE: {len(unique_leads)} unique leads ({len(all_leads)} total before dedup)")
    print(f"Searches run: {search_count}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    # Support CLI args for testing: python tools/discover_google_places.py wedding_venues "Boston, MA"
    if len(sys.argv) > 1:
        profile_arg = sys.argv[1]
        city_arg = sys.argv[2] if len(sys.argv) > 2 else None
        run(
            profiles=[profile_arg],
            cities_override=[city_arg] if city_arg else None,
        )
    else:
        run()
