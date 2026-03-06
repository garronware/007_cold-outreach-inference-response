"""
Automated reply monitor — scans Gmail for outreach replies and handles them.

Usage:
    python tools/auto_reply_monitor.py                # Dry run: show what would happen
    python tools/auto_reply_monitor.py --send          # Actually send draft replies
    python tools/auto_reply_monitor.py --send --log    # Send and append to log file
    python tools/auto_reply_monitor.py --regex         # Use regex fallback (no API cost)

Architecture:
    Tool layer: Gmail scanning, thread tracking, sending, logging (deterministic)
    Agent layer: Claude reads each reply, classifies it, drafts a response (reasoning)
    Fallback: regex-based classification if no ANTHROPIC_API_KEY is set or --regex flag
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth_helper import get_credentials

load_dotenv()

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
LOG_FILE = os.path.join(BASE_DIR, ".tmp", "reply_monitor_log.json")

OUTREACH_SUBJECT = "Wedding florist closing. Selling inventory."
MY_EMAIL = "garron.ware@gmail.com"

# Context for the LLM about who we are and what we're doing
OUTREACH_CONTEXT = """You are helping Garron respond to replies to his outreach emails.

Background: Garron's mom ran a floral & event design business in southern Vermont.
The business is closing, and Garron is helping her sell the inventory — a large
collection of professionally-sourced event decor products and floral supplies
(vases, containers, ribbon, ceremony structures, etc.). He emailed wedding venues,
florists, and event companies offering the inventory at ~35% of wholesale as a
single-lot acquisition. The inventory is in a warehouse in Manchester, VT, and
there's a photo gallery + video walkthrough on Google Drive (already linked in the
original outreach email).

Garron's tone: Personal, warm, not salesy. He's a son helping his mom, not a
B2B salesperson. Keep replies short (2-4 sentences max), friendly, and genuine.
Sign off as "Garron" (not "Garron Ware" or "Best regards").
"""

# ============================================================
# Tool Layer — Gmail operations (deterministic)
# ============================================================

def get_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def get_reply_threads(service):
    """Find all message threads that are replies to outreach emails."""
    query = f'subject:"{OUTREACH_SUBJECT}" -from:me'
    results = service.users().messages().list(
        userId="me", q=query, maxResults=200
    ).execute()
    return results.get("messages", [])


def get_thread_messages(service, thread_id):
    """Get all messages in a thread."""
    thread = service.users().threads().get(userId="me", id=thread_id).execute()
    return thread.get("messages", [])


def extract_message_info(msg):
    """Extract useful fields from a Gmail message object."""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

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
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "body": body[:2000],
        "snippet": msg.get("snippet", ""),
    }


def is_from_me(msg_info):
    """Check if a message was sent by us."""
    return MY_EMAIL in msg_info["from"].lower()


def we_already_replied(service, thread_id):
    """Check if we sent any reply in this thread (beyond the original outreach)."""
    messages = get_thread_messages(service, thread_id)
    from_me_count = 0
    for m in messages:
        for h in m["payload"]["headers"]:
            if h["name"].lower() == "from" and MY_EMAIL in h["value"].lower():
                from_me_count += 1
                break
    return from_me_count > 1


def get_latest_reply(service, thread_id):
    """Get the most recent non-me message in a thread."""
    messages = get_thread_messages(service, thread_id)
    for msg in reversed(messages):
        info = extract_message_info(msg)
        if not is_from_me(info):
            return info
    return None


def send_reply(service, msg_info, reply_text):
    """Send a reply in the same thread."""
    msg = MIMEText(reply_text)
    msg["to"] = msg_info["from"]
    msg["subject"] = "Re: " + msg_info["subject"].replace("Re: ", "")
    msg["In-Reply-To"] = msg_info["id"]
    msg["References"] = msg_info["id"]

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": msg_info["thread_id"]},
    ).execute()
    return result


def log_action(entry):
    """Append an entry to the log file."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log = json.load(f)

    log.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


# ============================================================
# Agent Layer — LLM-powered classification and reply drafting
# ============================================================

def get_anthropic_client():
    """Get Anthropic client, or None if no API key."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def llm_classify_and_draft(client, msg_info):
    """Use Claude to classify a reply and draft a response.

    Returns (category, reply_text) where reply_text is None for noise.
    Categories: noise, decline, interested, neutral
    """
    prompt = f"""Here is a reply to Garron's outreach email about selling floral/event inventory:

From: {msg_info['from']}
Date: {msg_info['date']}
Subject: {msg_info['subject']}

Body:
{msg_info['body'][:1500]}

---

Please analyze this reply and respond with a JSON object (no markdown fencing):

{{
  "category": "noise" | "decline" | "interested" | "neutral",
  "reasoning": "one sentence explaining why",
  "reply": "the reply text to send, or null for noise"
}}

Category definitions:
- "noise": Auto-replies, out-of-office, bounces, "no longer with company", generic auto-responders, email redirects ("please send to X instead"). These get NO reply.
- "decline": Polite refusals, "not interested", "too far", "doesn't align", "have to pass", well-wishes with a no. These get a gracious short reply.
- "interested": Asking about price, wanting to visit, requesting more info, expressing genuine interest. These get an engaged reply.
- "neutral": Anything else that's a real human reply but doesn't clearly fit above. Includes helpful suggestions, acknowledgments, etc. These get a friendly reply.

Reply guidelines:
- 2-4 sentences max. Short and genuine.
- Address them by first name (find it in the From header or email signature).
- For declines: "Totally understand" + offer to pass it along if they know someone.
- For interested: Answer their specific question. Price is ~35% of wholesale. Warehouse is in Manchester, VT. Photo gallery was in the original email.
- For neutral: Thank them, keep the door open without being pushy.
- Always sign off with just "Garron" on its own line.
- Do NOT repeat the photo gallery link — it was already in the original email.
- Do NOT be salesy. Garron is a son helping his mom, not a salesperson."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=OUTREACH_CONTEXT,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse the JSON response
    text = response.content[0].text.strip()
    # Handle potential markdown fencing
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    result = json.loads(text)
    category = result["category"]
    reply_text = result.get("reply")

    # Null/none reply for noise
    if reply_text and reply_text.lower() == "null":
        reply_text = None

    return category, result.get("reasoning", ""), reply_text


# ============================================================
# Regex Fallback — for when no API key is available
# ============================================================

NOISE_PATTERNS = [
    r"mailer-daemon", r"postmaster", r"mail delivery", r"delivery status",
    r"undeliverable", r"out of office", r"out-of-office", r"auto.?reply",
    r"automatic reply", r"away from the office", r"away from my desk",
    r"on vacation", r"no longer with", r"no longer works", r"no longer be with",
    r"this mailbox is not monitored", r"do not reply", r"noreply", r"no-reply",
    r"has left the company", r"is no longer", r"left the organization",
    r"currently out", r"currently away", r"i will return", r"i will be returning",
    r"please send all emails .{0,30} to", r"please direct .{0,30} to",
    r"please contact .{0,30} instead", r"submit an inquiry",
    r"this email is no longer monitored", r"out of town .{0,30} return",
    r"congratulations on your engagement", r"moved on for a new opportunity",
    r"for .{0,20} inquiries.{0,10}(please|contact|email|reach)",
]

DECLINE_PATTERNS = [
    r"not interested", r"no thank", r"no,? thank", r"have to pass",
    r"i'?ll have to pass", r"pass on this", r"not .{0,20}position",
    r"not .{0,20}looking", r"not .{0,20}right fit", r"not .{0,20}need",
    r"don'?t .{0,20}need", r"won'?t be", r"unable to", r"not at this time",
    r"good luck", r"best of luck", r"wish you .{0,10}(luck|best)",
    r"wishing you .{0,10}(luck|best)", r"unsubscribe", r"remove me",
    r"a bit far", r"too far", r"doesn'?t align", r"don'?t feel this align",
    r"not .{0,20}align", r"doesn'?t .{0,20}align",
    r"unfortunately.{0,30}(not|can'?t|won'?t|no room|no space)",
]

INTEREST_PATTERNS = [
    r"interested", r"tell me more", r"more info", r"how much", r"price",
    r"cost", r"photos", r"pictures", r"visit", r"come see", r"pick up",
    r"deliver", r"call me", r"phone", r"let'?s talk", r"schedule", r"meet",
    r"would love", r"sounds great", r"very interested",
    r"vendor list", r"preferred vendor",
]


def normalize_text(text):
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return text


def regex_classify_and_draft(msg_info):
    """Regex-based fallback for classification and reply drafting."""
    text = normalize_text(
        msg_info["from"] + " " + msg_info["subject"] + " " +
        msg_info["body"] + " " + msg_info["snippet"]
    ).lower()

    category = "neutral"
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text):
            category = "noise"
            break
    if category == "neutral":
        for pattern in DECLINE_PATTERNS:
            if re.search(pattern, text):
                category = "decline"
                break
    if category == "neutral":
        for pattern in INTEREST_PATTERNS:
            if re.search(pattern, text):
                category = "interested"
                break

    # Draft reply
    if category == "noise":
        return category, "regex match", None

    name = _extract_sender_name(msg_info["from"], msg_info["body"])

    if category == "decline":
        reply = (
            f"Hi {name},\n\n"
            "Totally understand — thanks for letting me know. "
            "If anything changes or you know someone who might be interested, "
            "feel free to pass this along.\n\n"
            "Best,\nGarron"
        )
        return category, "regex match", reply

    # Interested or neutral
    reply = f"Hi {name},\n\n"
    reply += "Thanks so much for getting back to me. "
    body = normalize_text(msg_info["body"]).lower()

    if any(re.search(p, body) for p in [r"how much", r"price", r"cost"]):
        reply += (
            "We're looking for roughly 35% of wholesale for the full lot. "
            "Happy to discuss specifics — the photo gallery and video "
            "walkthrough are in the original email below.\n\n"
            "Would you like to set up a time to chat?\n\n"
        )
    elif any(re.search(p, body) for p in [r"visit", r"come see", r"pick up", r"meet"]):
        reply += (
            "You're absolutely welcome to come see everything in person. "
            "The warehouse is in Manchester, VT. "
            "What days work best for you?\n\n"
        )
    elif any(re.search(p, body) for p in [r"take a look", r"i'?ll .{0,20}look"]):
        reply += (
            "Sounds great! Let me know if you have any questions "
            "after looking things over.\n\n"
        )
    else:
        reply += (
            "I'd love to chat more about this. "
            "Would you like to set up a time to talk or come see "
            "the inventory in person?\n\n"
        )

    reply += "Best,\nGarron"
    return category, "regex match", reply


def _extract_sender_name(from_header, body):
    """Pull a first name from From header or email body signature."""
    raw_name = from_header.split("<")[0].strip().strip('"')
    business_words = {"events", "sales", "info", "manager", "team", "leads",
                      "inc", "llc", "group", "flowers", "florist", "florists"}
    if not raw_name or "@" in raw_name:
        raw_name = ""

    name_words = raw_name.lower().split()
    is_business = (
        not raw_name or
        any(w in business_words for w in name_words) or
        "&" in raw_name or
        len(name_words) > 3
    )

    if is_business:
        sign_off = re.search(
            r"(?:^|\n)\s*[-\u2013\u2014]?\s*([A-Z][a-z]{2,15})\s*$",
            body, re.MULTILINE
        )
        if sign_off:
            return sign_off.group(1)
        return "there"

    first = raw_name.split()[0]
    if "," in raw_name:
        parts = raw_name.split(",")
        if len(parts) == 2:
            first = parts[1].strip().split()[0]
    return first


# ============================================================
# Main loop
# ============================================================

def run(send: bool = False, write_log: bool = False, use_regex: bool = False):
    """Main monitor loop."""
    # Determine which engine to use
    anthropic_client = None
    if not use_regex:
        anthropic_client = get_anthropic_client()

    engine = "regex" if anthropic_client is None else "claude"
    if engine == "regex" and not use_regex:
        print("No ANTHROPIC_API_KEY found — falling back to regex mode.")

    print(f"{'='*60}")
    print(f"Reply Monitor — {'LIVE' if send else 'DRY RUN'} ({engine} engine)")
    print(f"{'='*60}")

    service = get_service()
    print(f'Searching for replies to: "{OUTREACH_SUBJECT}"')
    messages = get_reply_threads(service)

    if not messages:
        print("\nNo replies found.")
        return

    # Group by thread
    seen_threads = set()
    unique_threads = []
    for msg_info in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_info["id"], format="metadata",
            metadataHeaders=["From"]
        ).execute()
        thread_id = msg.get("threadId")
        if thread_id not in seen_threads:
            seen_threads.add(thread_id)
            unique_threads.append(thread_id)

    print(f"Found {len(unique_threads)} reply threads.\n")

    stats = {"already_replied": 0, "noise": 0, "decline": 0,
             "interested": 0, "neutral": 0, "sent": 0, "errors": 0}

    for thread_id in unique_threads:
        if we_already_replied(service, thread_id):
            stats["already_replied"] += 1
            continue

        reply = get_latest_reply(service, thread_id)
        if not reply:
            continue

        # Classify and draft using chosen engine
        if engine == "claude":
            try:
                category, reasoning, reply_text = llm_classify_and_draft(
                    anthropic_client, reply
                )
            except Exception as e:
                print(f"  LLM error ({e}), falling back to regex")
                category, reasoning, reply_text = regex_classify_and_draft(reply)
        else:
            category, reasoning, reply_text = regex_classify_and_draft(reply)

        stats[category] += 1

        sender = reply["from"][:60]
        print(f"[{category.upper()}] {sender}")
        print(f"  Snippet: {reply['snippet'][:120]}")
        if engine == "claude":
            print(f"  Reasoning: {reasoning}")

        if reply_text is None:
            print(f"  -> No reply needed ({category})")
            continue

        print(f"  -> Draft reply:")
        for line in reply_text.split("\n"):
            print(f"     {line}")

        if send:
            try:
                result = send_reply(service, reply, reply_text)
                stats["sent"] += 1
                print(f"  -> SENT (msg: {result['id']})")

                if write_log:
                    log_action({
                        "timestamp": datetime.now().isoformat(),
                        "thread_id": thread_id,
                        "from": reply["from"],
                        "category": category,
                        "reasoning": reasoning,
                        "engine": engine,
                        "reply_sent": True,
                        "reply_text": reply_text,
                        "message_id": result["id"],
                    })
            except Exception as e:
                stats["errors"] += 1
                print(f"  -> ERROR: {e}")
        else:
            print(f"  -> [DRY RUN — not sent]")

        print()

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary ({engine} engine):")
    print(f"  Already replied to: {stats['already_replied']}")
    print(f"  Noise (bounces/auto-replies): {stats['noise']}")
    print(f"  Declines: {stats['decline']}")
    print(f"  Interested: {stats['interested']}")
    print(f"  Neutral: {stats['neutral']}")
    if send:
        print(f"  Replies sent: {stats['sent']}")
        if stats["errors"]:
            print(f"  Errors: {stats['errors']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    should_send = "--send" in sys.argv
    should_log = "--log" in sys.argv
    use_regex = "--regex" in sys.argv
    run(send=should_send, write_log=should_log, use_regex=use_regex)
