"""
Gmail email sender for outreach pipeline.

Usage:
    python tools/send_gmail.py --dry-run                # Preview all unsent emails
    python tools/send_gmail.py --dry-run --limit 3      # Preview first 3
    python tools/send_gmail.py --send --to you@email    # Test send to yourself
    python tools/send_gmail.py --send --limit 2         # Send to first 2 unsent leads
    python tools/send_gmail.py --send                   # Send to all unsent leads

Reads leads from Google Sheet. Only sends to rows that have an email address
and no existing Email Status. Updates the sheet after each send.
"""

from __future__ import annotations

import argparse
import base64
import os
import smtplib
import socket
import sys
import time
from datetime import date
from email.mime.text import MIMEText

import dns.resolver
import markdown
from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth_helper import get_credentials

load_dotenv()

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
TEMPLATE_FILE = os.path.join(BASE_DIR, "inventory_liquidation_email_template.md")

# Google Sheet column indexes (0-based, matching SHEET_HEADERS in sheets_tracker.py)
COL_COMPANY = 0
COL_EMAIL = 2
COL_EMAIL_SENT = 14     # Column O
COL_EMAIL_STATUS = 15   # Column P


def load_template():
    """Load email template, extract subject and body, convert body to HTML."""
    with open(TEMPLATE_FILE) as f:
        lines = f.readlines()

    # Line 1: "**Email Template 5**" (skip)
    # Line 2: blank (skip)
    # Line 3: "**Subject:** actual subject text"
    # Line 4: blank (skip)
    # Line 5+: email body in markdown
    subject_line = lines[2].strip()
    subject = subject_line.replace("**Subject:** ", "")

    body_md = "".join(lines[4:])

    body_html = markdown.markdown(body_md)

    html = (
        '<html>\n'
        '<body style="font-family: Arial, sans-serif; font-size: 14px; '
        'line-height: 1.6; color: #333;">\n'
        f'{body_html}\n'
        '</body>\n'
        '</html>'
    )

    return subject, html, body_md


def get_gmail_service():
    """Build the Gmail API service."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def get_sheets_service():
    """Build the Google Sheets API service."""
    creds = get_credentials()
    return build("sheets", "v4", credentials=creds)


def get_unsent_leads(sheets_service, spreadsheet_id):
    """Read all rows from Sheet, return those with email but no Email Status."""
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Leads!A:S",
    ).execute()

    rows = result.get("values", [])
    if len(rows) <= 1:
        return []

    leads = []
    for i, row in enumerate(rows[1:], start=2):  # start=2: row 1 is header
        # Pad row to full width so index access doesn't fail
        while len(row) < 19:
            row.append("")

        email = row[COL_EMAIL].strip()
        email_status = row[COL_EMAIL_STATUS].strip()
        company = row[COL_COMPANY].strip()

        if email and not email_status:
            leads.append({
                "row_num": i,
                "company": company,
                "email": email,
            })

    return leads


def verify_email(email):
    """Verify an email address via MX lookup and SMTP check.

    Returns (is_valid, reason) tuple.
    """
    domain = email.split("@")[-1]

    # Step 1: MX record lookup
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_host = str(mx_records[0].exchange).rstrip(".")
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers, dns.exception.DNSException):
        return False, "no MX records (dead domain)"

    # Step 2: SMTP check — ask the mail server if the address exists
    try:
        with smtplib.SMTP(mx_host, 25, timeout=10) as smtp:
            smtp.helo("gmail.com")
            smtp.mail("verify@gmail.com")
            code, _ = smtp.rcpt(email)
            if code == 250:
                return True, "verified"
            elif code == 550:
                return False, "mailbox does not exist"
            else:
                # Ambiguous response (catch-all, greylisting) — assume valid
                return True, f"smtp code {code} (assumed ok)"
    except (smtplib.SMTPException, socket.timeout, socket.error, OSError):
        # SMTP check failed (blocked, timeout) — MX exists so assume valid
        return True, "mx valid (smtp check skipped)"


def create_message(to_email, subject, html_body):
    """Create a MIME email message."""
    msg = MIMEText(html_body, "html")
    msg["to"] = to_email
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_email(gmail_service, message):
    """Send an email via Gmail API."""
    return gmail_service.users().messages().send(
        userId="me",
        body=message,
    ).execute()


def update_sheet_row(sheets_service, spreadsheet_id, row_num, status="sent"):
    """Mark a row's email status in the Google Sheet."""
    today = date.today().isoformat()

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"Leads!O{row_num}:P{row_num}",
        valueInputOption="RAW",
        body={"values": [[today, status]]},
    ).execute()


def main():
    parser = argparse.ArgumentParser(description="Send outreach emails via Gmail API")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="Preview emails without sending")
    mode.add_argument("--send", action="store_true",
                      help="Actually send emails")

    parser.add_argument("--to", type=str,
                        help="Send test email to this address (ignores Sheet)")
    parser.add_argument("--limit", type=int,
                        help="Max number of emails to send")
    parser.add_argument("--delay", type=int, default=5,
                        help="Seconds between sends (default: 5)")

    args = parser.parse_args()

    # Load template
    subject, html_body, body_md = load_template()

    # --- Test mode: send to a specific address ---
    if args.to:
        print(f"\n{'='*50}")
        print("TEST EMAIL")
        print(f"{'='*50}")
        print(f"To: {args.to}")
        print(f"Subject: {subject}")
        print(f"\n--- Body (markdown) ---\n{body_md}")

        if args.send:
            gmail = get_gmail_service()
            message = create_message(args.to, subject, html_body)
            result = send_email(gmail, message)
            print(f"\nSent! Message ID: {result['id']}")
        else:
            print("\n[DRY RUN — no email sent]")
        return

    # --- Normal mode: send to leads from Sheet ---
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        print("Error: GOOGLE_SHEETS_SPREADSHEET_ID not set in .env")
        sys.exit(1)

    sheets = get_sheets_service()
    leads = get_unsent_leads(sheets, spreadsheet_id)

    if not leads:
        print("No unsent leads with email addresses found in the Sheet.")
        return

    if args.limit:
        leads = leads[:args.limit]

    print(f"\n{'='*50}")
    print(f"{'DRY RUN' if args.dry_run else 'SENDING'}: {len(leads)} emails")
    print(f"Subject: {subject}")
    print(f"{'='*50}\n")

    sent = 0
    errors = 0
    invalid = 0
    gmail = None
    if args.send:
        gmail = get_gmail_service()

    for i, lead in enumerate(leads):
        print(f"[{i+1}/{len(leads)}] {lead['company']} — {lead['email']}", end="")

        if args.dry_run:
            is_valid, reason = verify_email(lead["email"])
            status = "ok" if is_valid else "INVALID"
            print(f" [{status}: {reason}]")
            if not is_valid:
                invalid += 1
            continue

        # Verify before sending
        is_valid, reason = verify_email(lead["email"])
        if not is_valid:
            invalid += 1
            update_sheet_row(sheets, spreadsheet_id, lead["row_num"],
                             status=f"invalid: {reason}")
            print(f" — SKIPPED ({reason})")
            continue

        try:
            message = create_message(lead["email"], subject, html_body)
            result = send_email(gmail, message)
            update_sheet_row(sheets, spreadsheet_id, lead["row_num"])
            sent += 1
            print(f" — sent (msg: {result['id']})")
        except Exception as e:
            errors += 1
            print(f" — ERROR: {e}")

        # Delay between sends (skip after last email)
        if i < len(leads) - 1:
            time.sleep(args.delay)

    print(f"\n{'='*50}")
    print(f"Summary: {sent} sent, {invalid} invalid, {errors} errors, "
          f"{len(leads) - sent - invalid - errors} previewed")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
