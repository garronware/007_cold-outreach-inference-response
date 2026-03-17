"""
Build site data — extracts stats from pipeline data files for the story page.

Usage:
    python tools/build_site_data.py

Reads .tmp/*.json and Google Sheets to produce site/src/data/stats.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
QUALIFIED_FILE = os.path.join(BASE_DIR, ".tmp", "qualified_leads.json")
REPLY_LOG_FILE = os.path.join(BASE_DIR, ".tmp", "reply_monitor_log.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "site", "src", "data", "stats.json")

# Manual overrides for stats that the log file hasn't caught up to.
# Update these when you know the real numbers differ from the log.
OVERRIDES = {
    "replies_interested": 2,  # Meggie + Elyse confirmed interested
}

# The Knot scraper was run for these metro areas.
# Since city-level data is inconsistent (many leads have empty or state-level
# location), we track metros based on the discovery runs that were executed.
METROS = ["Boston", "New York", "Albany Capital Region", "Hudson Valley"]

# Known API cost (not derivable from data files)
API_COST = 4.38


def count_leads():
    """Count total qualified leads."""
    if not os.path.exists(QUALIFIED_FILE):
        print(f"Warning: {QUALIFIED_FILE} not found, using 0")
        return 0

    with open(QUALIFIED_FILE) as f:
        leads = json.load(f)
    return len(leads)


def count_replies():
    """Count replies by category from the monitor log."""
    if not os.path.exists(REPLY_LOG_FILE):
        print(f"Warning: {REPLY_LOG_FILE} not found, using 0s")
        return {"total": 0, "interested": 0, "considering": 0, "declined": 0}

    with open(REPLY_LOG_FILE) as f:
        replies = json.load(f)

    counts = {"interested": 0, "neutral": 0, "decline": 0}
    for reply in replies:
        cat = reply.get("category", "unknown")
        if cat in counts:
            counts[cat] += 1

    return {
        "total": len(replies),
        "interested": OVERRIDES.get("replies_interested", counts["interested"]),
        "considering": counts["neutral"],
        "declined": counts["decline"],
    }


def count_emails_sent():
    """Count emails sent from Google Sheets (column O = 'Email Sent')."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from google_auth_helper import get_credentials
        from googleapiclient.discovery import build

        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        if not spreadsheet_id:
            print("Warning: No GOOGLE_SHEETS_SPREADSHEET_ID in .env")
            return None

        creds = get_credentials()
        service = build("sheets", "v4", credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Leads!O:O",
        ).execute()

        rows = result.get("values", [])
        # Skip header, count non-empty values
        sent_count = sum(1 for row in rows[1:] if row and row[0].strip())
        return sent_count

    except Exception as e:
        print(f"Warning: Sheets API failed ({e}), will use cached value")
        return None


def load_cached_emails_sent():
    """Load emails_sent from a previous stats.json if it exists."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            cached = json.load(f)
        return cached.get("emails_sent", 362)
    return 362  # known baseline


def build_stats():
    """Build the full stats object."""
    leads_total = count_leads()
    replies = count_replies()
    emails_sent = count_emails_sent()

    if emails_sent is None:
        emails_sent = load_cached_emails_sent()
        print(f"Using cached emails_sent: {emails_sent}")

    stats = {
        "leads_total": leads_total,
        "metros": METROS,
        "metros_count": len(METROS),
        "emails_sent": emails_sent,
        "emails_errors": 0,
        "api_cost": API_COST,
        "replies_total": replies["total"],
        "replies_interested": replies["interested"],
        "replies_considering": replies["considering"],
        "replies_declined": replies["declined"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return stats


def main():
    stats = build_stats()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\nStats written to {OUTPUT_FILE}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
