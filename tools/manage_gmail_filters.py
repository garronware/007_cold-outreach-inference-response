"""
Create Gmail labels and filters for the outreach campaign.

Creates:
  - "Inventory/Bounces" label with filter to auto-archive bounce messages
  - "Inventory/Replies" label with filter to label incoming replies

Usage:
    python tools/manage_gmail_filters.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from google_auth_helper import get_credentials


def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def create_label(service, name):
    """Create a Gmail label. Returns the label ID (existing or new)."""
    # Check if label already exists
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == name:
            print(f"  Label '{name}' already exists (id: {label['id']})")
            return label["id"]

    label_body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=label_body).execute()
    print(f"  Created label '{name}' (id: {created['id']})")
    return created["id"]


def create_filter(service, criteria, action, description):
    """Create a Gmail filter. Skips if a matching filter already exists."""
    # List existing filters to avoid duplicates
    results = service.users().settings().filters().list(userId="me").execute()
    for f in results.get("filter", []):
        if f.get("criteria", {}).get("from") == criteria.get("from") and \
           f.get("criteria", {}).get("subject") == criteria.get("subject"):
            print(f"  Filter already exists for: {description}")
            return

    filter_body = {
        "criteria": criteria,
        "action": action,
    }
    service.users().settings().filters().create(userId="me", body=filter_body).execute()
    print(f"  Created filter: {description}")


def main():
    print("Connecting to Gmail API...")
    service = get_gmail_service()

    # --- Create labels ---
    print("\nCreating labels...")
    bounces_label_id = create_label(service, "Inventory/Bounces")
    replies_label_id = create_label(service, "Inventory/Replies")

    # --- Create filters ---
    print("\nCreating filters...")

    # Bounce filter: catch mailer-daemon and postmaster messages, skip inbox
    create_filter(
        service,
        criteria={"from": "mailer-daemon@googlemail.com OR postmaster"},
        action={
            "addLabelIds": [bounces_label_id],
            "removeLabelIds": ["INBOX"],
        },
        description="Bounces -> skip inbox, label Inventory/Bounces",
    )

    # Reply filter: catch replies to outreach subject
    create_filter(
        service,
        criteria={"subject": "Wedding florist closing. Selling inventory."},
        action={
            "addLabelIds": [replies_label_id],
        },
        description="Replies about outreach -> label Inventory/Replies",
    )

    print("\nDone! Your Gmail now has:")
    print("  - Bounces will skip your inbox and go to 'Inventory/Bounces'")
    print("  - Replies to outreach will be labeled 'Inventory/Replies' (and stay in inbox)")


if __name__ == "__main__":
    main()
