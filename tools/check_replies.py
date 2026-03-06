"""
Scan Gmail for replies to outreach emails and classify them.

Usage:
    python tools/check_replies.py                # Show all interesting replies
    python tools/check_replies.py --all           # Show all replies including noise
    python tools/check_replies.py --draft-reply   # Draft replies for interesting messages

Searches for threads matching the outreach subject, filters out bounces
and auto-replies, and surfaces messages that need a human response.
"""

from __future__ import annotations

import base64
import re
import sys
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from google_auth_helper import get_credentials

OUTREACH_SUBJECT = "Wedding florist closing. Selling inventory."

# Patterns that indicate noise (not a real reply)
NOISE_PATTERNS = [
    r"mailer-daemon",
    r"postmaster",
    r"mail delivery",
    r"delivery status",
    r"undeliverable",
    r"out of office",
    r"out-of-office",
    r"auto.?reply",
    r"automatic reply",
    r"away from",
    r"on vacation",
    r"no longer with",
    r"this mailbox is not monitored",
    r"do not reply",
    r"noreply",
    r"no-reply",
]

# Patterns that indicate genuine interest
INTEREST_PATTERNS = [
    r"interested",
    r"tell me more",
    r"more info",
    r"how much",
    r"price",
    r"cost",
    r"photos",
    r"pictures",
    r"visit",
    r"come see",
    r"pick up",
    r"deliver",
    r"inventory",
    r"available",
    r"call me",
    r"phone",
    r"let'?s talk",
    r"schedule",
    r"meet",
]


def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def get_threads(service):
    """Find all threads that are replies to outreach emails."""
    query = f'subject:"{OUTREACH_SUBJECT}" -from:me'
    results = service.users().messages().list(
        userId="me", q=query, maxResults=200
    ).execute()
    return results.get("messages", [])


def get_message_detail(service, msg_id):
    """Get full message details."""
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

    # Extract body text
    body = ""
    payload = msg["payload"]
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break
            elif part["mimeType"] == "text/html" and "data" in part.get("body", {}):
                raw = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                body = re.sub(r"<[^>]+>", " ", raw)
                body = re.sub(r"\s+", " ", body).strip()
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return {
        "id": msg_id,
        "thread_id": msg.get("threadId"),
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "body": body[:2000],  # Truncate very long messages
        "snippet": msg.get("snippet", ""),
    }


def classify_message(msg):
    """Classify a message as noise, interested, or neutral."""
    text = (msg["from"] + " " + msg["body"] + " " + msg["snippet"]).lower()

    # Check noise patterns first
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text):
            return "noise"

    # Check interest patterns
    for pattern in INTEREST_PATTERNS:
        if re.search(pattern, text):
            return "interested"

    return "neutral"


def draft_reply_text(msg):
    """Generate a draft reply for an interesting message."""
    sender_name = msg["from"].split("<")[0].strip().strip('"')
    if not sender_name or "@" in sender_name:
        sender_name = "there"

    body = msg["body"].lower()

    # Base reply - personal and warm
    reply = f"Hi {sender_name},\n\n"
    reply += "Thanks so much for getting back to me. "

    if any(re.search(p, body) for p in [r"how much", r"price", r"cost"]):
        reply += (
            "We're looking for roughly 35% of wholesale for the full lot. "
            "Happy to discuss specifics if you'd like to take a look at the "
            "photo gallery: https://drive.google.com/drive/folders/"
            "1oYxSRocMV7Mm--zOW4nqo5nf-QhS2abW?usp=sharing\n\n"
        )
    elif any(re.search(p, body) for p in [r"visit", r"come see", r"pick up", r"meet"]):
        reply += (
            "You're absolutely welcome to come see everything in person. "
            "The warehouse is in Manchester, VT. "
            "What days work best for you?\n\n"
        )
    elif any(re.search(p, body) for p in [r"photo", r"picture", r"image"]):
        reply += (
            "Here's the full photo gallery and video walkthrough: "
            "https://drive.google.com/drive/folders/"
            "1oYxSRocMV7Mm--zOW4nqo5nf-QhS2abW?usp=sharing\n\n"
            "Let me know if you have any questions after taking a look.\n\n"
        )
    else:
        reply += (
            "I'd love to chat more about this. The full photo gallery is here: "
            "https://drive.google.com/drive/folders/"
            "1oYxSRocMV7Mm--zOW4nqo5nf-QhS2abW?usp=sharing\n\n"
            "Would you like to set up a time to talk or come see "
            "the inventory in person?\n\n"
        )

    reply += "Best,\nGarron"
    return reply


def main():
    show_all = "--all" in sys.argv
    draft_replies = "--draft-reply" in sys.argv

    print("Connecting to Gmail...")
    service = get_gmail_service()

    print(f'Searching for replies to: "{OUTREACH_SUBJECT}"')
    messages = get_threads(service)

    if not messages:
        print("\nNo replies found.")
        return

    print(f"Found {len(messages)} replies. Classifying...\n")

    classified = {"interested": [], "neutral": [], "noise": []}

    for msg_info in messages:
        detail = get_message_detail(service, msg_info["id"])
        category = classify_message(detail)
        detail["category"] = category
        classified[category].append(detail)

    # Print results
    interesting = classified["interested"] + classified["neutral"]

    if interesting:
        print(f"{'='*60}")
        print(f"REPLIES THAT NEED ATTENTION ({len(interesting)})")
        print(f"{'='*60}")

        for msg in interesting:
            tag = "INTERESTED" if msg["category"] == "interested" else "NEUTRAL"
            print(f"\n[{tag}] From: {msg['from']}")
            print(f"  Date: {msg['date']}")
            print(f"  Subject: {msg['subject']}")
            print(f"  Preview: {msg['snippet'][:200]}")

            if draft_replies:
                reply = draft_reply_text(msg)
                print(f"\n  --- DRAFT REPLY ---")
                for line in reply.split("\n"):
                    print(f"  {line}")
                print(f"  --- END DRAFT ---")

            print()
    else:
        print("No interesting replies found.")

    if show_all and classified["noise"]:
        print(f"\n{'='*60}")
        print(f"NOISE / AUTO-REPLIES ({len(classified['noise'])})")
        print(f"{'='*60}")
        for msg in classified["noise"]:
            print(f"  {msg['from'][:50]} — {msg['snippet'][:80]}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Interested: {len(classified['interested'])}")
    print(f"  Neutral (review needed): {len(classified['neutral'])}")
    print(f"  Noise (auto-replies/bounces): {len(classified['noise'])}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
