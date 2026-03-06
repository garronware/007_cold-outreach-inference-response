"""
Qualify and merge leads from Google Places and The Knot.

Usage:
    python tools/qualify_leads.py              # Run with default thresholds
    python tools/qualify_leads.py --no-filter  # Skip filtering, just merge and dedup

Reads from .tmp/raw_leads_places.json and .tmp/raw_leads_theknot.json.
Outputs qualified leads to .tmp/qualified_leads.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Optional
from urllib.parse import urlparse

# Paths
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PLACES_FILE = os.path.join(BASE_DIR, ".tmp", "raw_leads_places.json")
THEKNOT_FILE = os.path.join(BASE_DIR, ".tmp", "raw_leads_theknot.json")
OUTPUT_FILE = os.path.join(BASE_DIR, ".tmp", "qualified_leads.json")

# Qualification thresholds
THRESHOLDS = {
    "wedding_venues": {
        "min_review_count": 50,
    },
    "floral_designers": {
        "min_review_count": 30,
    },
}


def extract_domain(url: str) -> str:
    """Extract the root domain from a URL for dedup matching."""
    if not url:
        return ""
    try:
        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
        domain = parsed.netloc.lower()
        # Strip www.
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def normalize_name(name: str) -> str:
    """Normalize a business name for dedup matching."""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" llc", " inc", " ltd", " co", " company"]:
        name = name.replace(suffix, "")
    # Remove non-alphanumeric
    name = re.sub(r"[^a-z0-9\s]", "", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def merge_lead(places_lead: Optional[dict], theknot_lead: Optional[dict]) -> dict:
    """Merge data from both sources, preferring The Knot (richer data)."""
    merged = {
        "name": "",
        "address": "",
        "city": "",
        "state": "",
        "buyer_profile": "",
        "rating": None,
        "review_count": None,
        "website": "",
        "phone": "",
        "email": "",
        "price_level": "",
        "price_range": "",
        "capacity": "",
        "description": "",
        "sources": [],
        "place_id": "",
        "theknot_url": "",
    }

    if places_lead:
        merged["name"] = places_lead.get("name", "")
        merged["address"] = places_lead.get("address", "")
        merged["buyer_profile"] = places_lead.get("buyer_profile", "")
        merged["rating"] = places_lead.get("rating")
        merged["review_count"] = places_lead.get("review_count")
        merged["website"] = places_lead.get("website", "")
        merged["phone"] = places_lead.get("phone", "")
        merged["price_level"] = places_lead.get("price_level", "")
        merged["place_id"] = places_lead.get("place_id", "")
        merged["sources"].append("google_places")

        # Extract city/state from address
        addr = places_lead.get("address", "")
        parts = addr.split(",")
        if len(parts) >= 3:
            merged["city"] = parts[-3].strip()
            state_zip = parts[-2].strip()
            merged["state"] = state_zip.split()[0] if state_zip else ""

    if theknot_lead:
        # The Knot has richer data, so prefer it for overlapping fields
        merged["name"] = theknot_lead.get("name") or merged["name"]
        merged["buyer_profile"] = theknot_lead.get("buyer_profile") or merged["buyer_profile"]
        merged["website"] = theknot_lead.get("website") or merged["website"]
        merged["phone"] = theknot_lead.get("phone") or merged["phone"]
        merged["email"] = theknot_lead.get("email", "")
        merged["price_range"] = theknot_lead.get("price_range", "")
        merged["capacity"] = theknot_lead.get("capacity", "")
        merged["description"] = theknot_lead.get("description", "")
        merged["theknot_url"] = theknot_lead.get("profile_url", "")
        merged["state"] = theknot_lead.get("location") or merged["state"]
        merged["sources"].append("theknot")

        # Use higher review count from either source
        tk_reviews = theknot_lead.get("review_count")
        if tk_reviews and (merged["review_count"] is None or tk_reviews > merged["review_count"]):
            merged["review_count"] = tk_reviews

        # Use higher rating
        tk_rating = theknot_lead.get("rating")
        if tk_rating and (merged["rating"] is None or tk_rating > merged["rating"]):
            merged["rating"] = tk_rating

    return merged


def qualifies(lead: dict) -> bool:
    """Check if a lead meets the qualification thresholds."""
    profile = lead.get("buyer_profile", "")
    thresholds = THRESHOLDS.get(profile, {})

    min_reviews = thresholds.get("min_review_count", 0)
    review_count = lead.get("review_count") or 0

    # Pass if meets review threshold
    if review_count >= min_reviews:
        return True

    # Pass if has a The Knot profile (they're generally established businesses)
    if "theknot" in lead.get("sources", []):
        return True

    # Pass if we have a direct email (valuable regardless)
    if lead.get("email"):
        return True

    return False


def run(skip_filter: bool = False):
    """Merge, deduplicate, and qualify leads from both sources."""

    # Load sources (either or both may exist)
    places_leads = []
    theknot_leads = []

    if os.path.exists(PLACES_FILE):
        with open(PLACES_FILE) as f:
            places_leads = json.load(f)
        print(f"Loaded {len(places_leads)} leads from Google Places")
    else:
        print(f"No Google Places file found at {PLACES_FILE}")

    if os.path.exists(THEKNOT_FILE):
        with open(THEKNOT_FILE) as f:
            theknot_leads = json.load(f)
        print(f"Loaded {len(theknot_leads)} leads from The Knot")
    else:
        print(f"No The Knot file found at {THEKNOT_FILE}")

    if not places_leads and not theknot_leads:
        print("ERROR: No lead files found. Run discovery tools first.")
        sys.exit(1)

    # Build lookup indexes for dedup
    # Index by normalized name and by domain
    places_by_name = {}
    places_by_domain = {}
    for lead in places_leads:
        norm = normalize_name(lead.get("name", ""))
        if norm:
            places_by_name[norm] = lead
        domain = extract_domain(lead.get("website", ""))
        if domain:
            places_by_domain[domain] = lead

    # Process The Knot leads, matching with Places where possible
    matched_places_names = set()
    merged_leads = []

    for tk_lead in theknot_leads:
        tk_name = normalize_name(tk_lead.get("name", ""))
        tk_domain = extract_domain(tk_lead.get("website", ""))

        # Try to match with a Places lead
        places_match = None
        if tk_name in places_by_name:
            places_match = places_by_name[tk_name]
            matched_places_names.add(tk_name)
        elif tk_domain and tk_domain in places_by_domain:
            places_match = places_by_domain[tk_domain]
            matched_places_names.add(normalize_name(places_match.get("name", "")))

        merged = merge_lead(places_match, tk_lead)
        merged_leads.append(merged)

    # Add unmatched Places leads
    for lead in places_leads:
        norm = normalize_name(lead.get("name", ""))
        if norm not in matched_places_names:
            merged = merge_lead(lead, None)
            merged_leads.append(merged)

    print(f"\nMerged: {len(merged_leads)} total leads")
    both = sum(1 for l in merged_leads if len(l["sources"]) == 2)
    print(f"  From both sources: {both}")
    print(f"  Google Places only: {sum(1 for l in merged_leads if l['sources'] == ['google_places'])}")
    print(f"  The Knot only: {sum(1 for l in merged_leads if l['sources'] == ['theknot'])}")

    # Apply qualification filter
    if skip_filter:
        qualified = merged_leads
        print(f"\nSkipping filter: all {len(qualified)} leads included")
    else:
        qualified = [l for l in merged_leads if qualifies(l)]
        filtered_out = len(merged_leads) - len(qualified)
        print(f"\nQualified: {len(qualified)} leads (filtered out {filtered_out})")

    # Sort by review count descending
    qualified.sort(key=lambda l: l.get("review_count") or 0, reverse=True)

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(qualified, f, indent=2)

    # Stats
    with_email = sum(1 for l in qualified if l["email"])
    with_website = sum(1 for l in qualified if l["website"])
    with_phone = sum(1 for l in qualified if l["phone"])
    print(f"\nContact coverage:")
    print(f"  With email: {with_email} ({100*with_email//max(len(qualified),1)}%)")
    print(f"  With website: {with_website} ({100*with_website//max(len(qualified),1)}%)")
    print(f"  With phone: {with_phone} ({100*with_phone//max(len(qualified),1)}%)")
    print(f"  Need enrichment (no email): {len(qualified) - with_email}")
    print(f"\nOutput: {OUTPUT_FILE}")


if __name__ == "__main__":
    skip = "--no-filter" in sys.argv
    run(skip_filter=skip)
