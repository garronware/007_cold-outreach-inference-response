"""
Google Sheets tracker — lightweight CRM for outreach pipeline.

Usage:
    python tools/sheets_tracker.py create           # Create new tracking spreadsheet
    python tools/sheets_tracker.py import            # Import qualified leads into sheet
    python tools/sheets_tracker.py status            # Print summary stats
    python tools/sheets_tracker.py update ROW EMAIL_STATUS  # Update a row's status

Creates/manages a Google Sheet with lead data, email status, and notes.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth_helper import get_credentials

load_dotenv()

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
QUALIFIED_FILE = os.path.join(BASE_DIR, ".tmp", "qualified_leads.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

SHEET_HEADERS = [
    "Company",
    "Contact Name",
    "Email",
    "Phone",
    "Website",
    "Buyer Profile",
    "City",
    "State",
    "Review Count",
    "Rating",
    "Price Range",
    "Capacity",
    "Sources",
    "The Knot URL",
    "Email Sent",
    "Email Status",
    "Follow-Up Date",
    "Response",
    "Notes",
]


def get_sheets_service():
    """Build the Google Sheets API service."""
    creds = get_credentials()
    return build("sheets", "v4", credentials=creds)


def get_spreadsheet_id() -> Optional[str]:
    """Read the spreadsheet ID from .env."""
    return os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None


def save_spreadsheet_id(spreadsheet_id: str):
    """Save the spreadsheet ID to .env."""
    env_path = ENV_FILE
    with open(env_path, "r") as f:
        content = f.read()

    if "GOOGLE_SHEETS_SPREADSHEET_ID=" in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("GOOGLE_SHEETS_SPREADSHEET_ID="):
                lines[i] = f"GOOGLE_SHEETS_SPREADSHEET_ID={spreadsheet_id}"
                break
        content = "\n".join(lines)
    else:
        content += f"\nGOOGLE_SHEETS_SPREADSHEET_ID={spreadsheet_id}\n"

    with open(env_path, "w") as f:
        f.write(content)

    # Also update the runtime env
    os.environ["GOOGLE_SHEETS_SPREADSHEET_ID"] = spreadsheet_id


def create_spreadsheet():
    """Create a new tracking spreadsheet and save its ID."""
    service = get_sheets_service()

    spreadsheet = service.spreadsheets().create(
        body={
            "properties": {"title": "Inventory Liquidation — Lead Tracker"},
            "sheets": [
                {
                    "properties": {
                        "title": "Leads",
                        "gridProperties": {
                            "frozenRowCount": 1,
                        },
                    },
                },
            ],
        }
    ).execute()

    spreadsheet_id = spreadsheet["spreadsheetId"]
    spreadsheet_url = spreadsheet["spreadsheetUrl"]
    sheet_id = spreadsheet["sheets"][0]["properties"]["sheetId"]

    # Write headers
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Leads!A1",
        valueInputOption="RAW",
        body={"values": [SHEET_HEADERS]},
    ).execute()

    # Bold the header row
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {"bold": True},
                                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            }
                        },
                        "fields": "userEnteredFormat(textFormat,backgroundColor)",
                    }
                },
            ]
        },
    ).execute()

    save_spreadsheet_id(spreadsheet_id)
    print(f"Created spreadsheet: {spreadsheet_url}")
    print(f"Spreadsheet ID saved to .env: {spreadsheet_id}")
    return spreadsheet_id


def import_leads():
    """Import qualified leads into the tracking spreadsheet."""
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        print("No spreadsheet ID found. Run 'create' first.")
        sys.exit(1)

    if not os.path.exists(QUALIFIED_FILE):
        print(f"No qualified leads file at {QUALIFIED_FILE}. Run qualify_leads.py first.")
        sys.exit(1)

    with open(QUALIFIED_FILE) as f:
        leads = json.load(f)

    service = get_sheets_service()

    # Check existing data to avoid duplicates
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Leads!A:A",
    ).execute()
    existing_names = set()
    for row in result.get("values", [])[1:]:  # Skip header
        if row:
            existing_names.add(row[0].lower().strip())

    # Build rows for new leads only
    new_rows = []
    for lead in leads:
        if lead["name"].lower().strip() in existing_names:
            continue

        row = [
            lead.get("name", ""),
            "",  # Contact Name (filled during enrichment)
            lead.get("email", ""),
            lead.get("phone", ""),
            lead.get("website", ""),
            lead.get("buyer_profile", ""),
            lead.get("city", ""),
            lead.get("state", ""),
            lead.get("review_count") or "",
            lead.get("rating") or "",
            lead.get("price_range", ""),
            lead.get("capacity", ""),
            ", ".join(lead.get("sources", [])),
            lead.get("theknot_url", ""),
            "",  # Email Sent
            "",  # Email Status
            "",  # Follow-Up Date
            "",  # Response
            "",  # Notes
        ]
        new_rows.append(row)

    if not new_rows:
        print("No new leads to import (all already in sheet)")
        return

    # Append rows
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Leads!A:S",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()

    print(f"Imported {len(new_rows)} new leads (skipped {len(leads) - len(new_rows)} duplicates)")
    print(f"Total leads in file: {len(leads)}")


def print_status():
    """Print summary stats from the tracking sheet."""
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        print("No spreadsheet ID found. Run 'create' first.")
        return

    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Leads!A:S",
    ).execute()

    rows = result.get("values", [])
    if len(rows) <= 1:
        print("No leads in sheet yet.")
        return

    data_rows = rows[1:]
    total = len(data_rows)

    # Count by status (column P = index 15)
    statuses = {}
    for row in data_rows:
        status = row[15] if len(row) > 15 and row[15] else "Not Sent"
        statuses[status] = statuses.get(status, 0) + 1

    # Count with email (column C = index 2)
    with_email = sum(1 for row in data_rows if len(row) > 2 and row[2])

    print(f"\n{'='*40}")
    print(f"Lead Tracker Summary")
    print(f"{'='*40}")
    print(f"Total leads: {total}")
    print(f"With email: {with_email} ({100*with_email//total}%)")
    print(f"Need enrichment: {total - with_email}")
    print(f"\nEmail Status:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")


def update_row(row_num: int, status: str):
    """Update the email status for a specific row."""
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        print("No spreadsheet ID found.")
        return

    service = get_sheets_service()
    # Column P (Email Status) = column 16
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"Leads!P{row_num}",
        valueInputOption="RAW",
        body={"values": [[status]]},
    ).execute()
    print(f"Updated row {row_num} status to: {status}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/sheets_tracker.py [create|import|status|update]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        create_spreadsheet()
    elif command == "import":
        import_leads()
    elif command == "status":
        print_status()
    elif command == "update":
        if len(sys.argv) < 4:
            print("Usage: python tools/sheets_tracker.py update ROW_NUM STATUS")
            sys.exit(1)
        update_row(int(sys.argv[2]), sys.argv[3])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
