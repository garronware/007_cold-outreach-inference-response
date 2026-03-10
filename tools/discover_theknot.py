"""
Discover potential buyers using The Knot marketplace via Apify scraper.

Usage:
    python tools/discover_theknot.py                                # Full run (all categories, all cities)
    python tools/discover_theknot.py venues                         # Venues only, all cities
    python tools/discover_theknot.py florists boston                 # Florists in Boston only
    python tools/discover_theknot.py venues albany --min-price 10000 # Venues in Albany, $10k+ starting price

Actor: dionysus_way/the-knot-marketplace-scraper---wedding-vendor-leads
Outputs raw leads to .tmp/raw_leads_theknot.json.
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

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = "dionysus_way~the-knot-marketplace-scraper---wedding-vendor-leads"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", ".tmp", "raw_leads_theknot.json")

# URL patterns for The Knot marketplace
# Format: https://www.theknot.com/marketplace/{category}-{city}-{state}
SEARCHES = {
    "venues": {
        "url_category": "wedding-reception-venues",
        "max_pages": 5,
        "cities": [
            ("boston", "ma"), ("new-york", "ny"), ("albany", "ny"),
            ("hudson-valley", "ny"), ("philadelphia", "pa"),
            ("washington", "dc"), ("nashville", "tn"), ("chicago", "il"),
            ("miami", "fl"), ("los-angeles", "ca"), ("san-francisco", "ca"),
            ("denver", "co"), ("seattle", "wa"), ("charleston", "sc"),
            ("savannah", "ga"), ("austin", "tx"), ("dallas", "tx"),
        ],
    },
    "florists": {
        "url_category": "florists",
        "max_pages": 5,
        "cities": [
            ("boston", "ma"), ("new-york", "ny"), ("philadelphia", "pa"),
            ("washington", "dc"), ("nashville", "tn"), ("chicago", "il"),
            ("miami", "fl"), ("los-angeles", "ca"), ("san-francisco", "ca"),
            ("denver", "co"), ("seattle", "wa"),
        ],
    },
}

# Apify limits startUrls to 4 per run, so we batch
BATCH_SIZE = 4
POLL_INTERVAL = 10  # seconds
MAX_POLL_ATTEMPTS = 60  # 10 min max wait


def build_urls(category: str, cities: list, min_price: Optional[int] = None) -> list:
    """Build The Knot marketplace URLs for a category + city list."""
    url_cat = SEARCHES[category]["url_category"]
    urls = []
    for city, state in cities:
        url = f"https://www.theknot.com/marketplace/{url_cat}-{city}-{state}"
        if min_price:
            url += f"?minPrice={min_price}"
        urls.append(url)
    return urls


def run_actor(start_urls: list, max_pages: int) -> list:
    """Run the Apify actor and return results."""
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"
    payload = {
        "startUrls": start_urls,
        "maxPages": max_pages,
    }

    print(f"    Starting actor with {len(start_urls)} URLs, maxPages={max_pages}...")
    resp = requests.post(run_url, json=payload)
    if resp.status_code != 201:
        print(f"    ERROR starting actor: {resp.status_code} {resp.text[:200]}")
        return []

    run_data = resp.json().get("data", {})
    run_id = run_data.get("id")
    dataset_id = run_data.get("defaultDatasetId")

    # Poll for completion
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
    for attempt in range(MAX_POLL_ATTEMPTS):
        time.sleep(POLL_INTERVAL)
        status_resp = requests.get(status_url)
        status = status_resp.json().get("data", {}).get("status")
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            print(f"    Actor run {status}")
            return []
    else:
        print(f"    Timed out waiting for actor run")
        return []

    # Retrieve results
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
    items_resp = requests.get(items_url)
    items = items_resp.json()
    print(f"    Got {len(items)} results")
    return items


def normalize_theknot_lead(item: dict, category: str) -> dict:
    """Flatten a The Knot result into a clean lead record."""
    return {
        "source": "theknot",
        "buyer_profile": "wedding_venues" if category == "venues" else "floral_designers",
        "name": item.get("name", ""),
        "location": item.get("location", ""),
        "source_url": item.get("sourceUrl", ""),
        "profile_url": item.get("profileUrl", ""),
        "rating": item.get("rating"),
        "review_count": item.get("reviewCount"),
        "price_range": item.get("priceRange", ""),
        "capacity": item.get("capacity", ""),
        "venue_type": item.get("venueType", ""),
        "website": item.get("website", ""),
        "phone": item.get("phone", ""),
        "email": item.get("email", ""),
        "description": item.get("description", ""),
        "settings": item.get("settings", []),
        "services": item.get("services", []),
    }


def run(categories: Optional[list] = None, city_filter: Optional[str] = None,
        min_price: Optional[int] = None):
    """
    Run The Knot discovery.

    Args:
        categories: List of category keys (default: all)
        city_filter: If provided, only search this city slug (e.g. "boston")
        min_price: If provided, filter by minimum starting price (e.g. 10000)
    """
    if not APIFY_TOKEN:
        print("ERROR: APIFY_API_TOKEN not set in .env")
        sys.exit(1)

    all_leads = []
    target_categories = categories or list(SEARCHES.keys())

    for category in target_categories:
        config = SEARCHES.get(category)
        if not config:
            print(f"WARNING: Unknown category '{category}', skipping")
            continue

        cities = config["cities"]
        if city_filter:
            cities = [(c, s) for c, s in cities if c == city_filter]
            if not cities:
                print(f"WARNING: City '{city_filter}' not found for {category}")
                continue

        urls = build_urls(category, cities, min_price=min_price)
        max_pages = config["max_pages"]

        print(f"\n{'='*60}")
        print(f"Category: {category} ({len(urls)} city URLs)")
        print(f"{'='*60}")

        # Batch URLs (Apify limits to 4 per run)
        for i in range(0, len(urls), BATCH_SIZE):
            batch = urls[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(urls) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"\n  Batch {batch_num}/{total_batches}:")
            for url in batch:
                print(f"    - {url}")

            items = run_actor(batch, max_pages)
            for item in items:
                lead = normalize_theknot_lead(item, category)
                all_leads.append(lead)

    # Merge with existing data from prior runs (so we don't overwrite)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing_leads = json.load(f)
        all_leads = existing_leads + all_leads

    # Deduplicate by name + location
    seen = set()
    unique_leads = []
    for lead in all_leads:
        key = (lead["name"].lower().strip(), lead["location"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_leads.append(lead)

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(unique_leads, f, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE: {len(unique_leads)} unique leads ({len(all_leads)} total before dedup)")
    print(f"Output: {OUTPUT_FILE}")

    # Stats
    with_email = sum(1 for l in unique_leads if l["email"])
    with_website = sum(1 for l in unique_leads if l["website"])
    print(f"With email: {with_email} ({100*with_email//max(len(unique_leads),1)}%)")
    print(f"With website: {with_website} ({100*with_website//max(len(unique_leads),1)}%)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Discover leads from The Knot marketplace")
    parser.add_argument("category", nargs="?", help="Category to search (venues, florists)")
    parser.add_argument("city", nargs="?", help="City slug to filter (e.g. boston, albany)")
    parser.add_argument("--min-price", type=int, help="Minimum starting price filter (e.g. 10000)")

    args = parser.parse_args()

    categories = [args.category] if args.category else None
    run(categories=categories, city_filter=args.city, min_price=args.min_price)
