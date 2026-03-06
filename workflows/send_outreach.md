# Send Outreach Emails

## Overview

Send the finalized email template to qualified leads via Gmail API. Reads leads from the Google Sheet, sends HTML-formatted emails, and updates the sheet with send status.

## Prerequisites

- `qualified_leads.json` imported into Google Sheet (via `sheets_tracker.py import`)
- Email template finalized at `inventory_liquidation_email_template.md`
- OAuth token cached in `token.json` (run any sheets command first to trigger auth)
- `markdown` Python package installed (`pip install markdown`)

## Commands

```bash
source venv/bin/activate

# Preview emails without sending (safe)
python tools/send_gmail.py --dry-run --limit 3

# Send a test email to yourself
python tools/send_gmail.py --send --to your@email.com

# Send to first 2 unsent leads (real send)
python tools/send_gmail.py --send --limit 2

# Send to ALL unsent leads
python tools/send_gmail.py --send

# Send with custom delay between emails (default is 5 seconds)
python tools/send_gmail.py --send --delay 10
```

## How It Works

1. Loads template from `inventory_liquidation_email_template.md`
2. Extracts subject line, converts body from markdown to HTML
3. Reads all rows from Google Sheet
4. Filters to rows that have an email address AND no Email Status yet
5. For each lead: sends email, updates Sheet (Email Sent = date, Email Status = "sent")
6. Waits `--delay` seconds between each send (default 5s)

## Safety

- Default mode is `--dry-run` — must explicitly pass `--send` to deliver
- `--to` flag sends to a specific address without touching the Sheet (for testing)
- `--limit` flag caps how many emails go out in one run
- The tool skips any lead that already has an Email Status in the Sheet (no double-sends)

## Google Sheet Columns Updated

- **Column O (Email Sent):** Date the email was sent (YYYY-MM-DD)
- **Column P (Email Status):** Set to "sent"

## Troubleshooting

- **"No unsent leads found"**: All leads in the Sheet already have an Email Status. Check column P.
- **OAuth errors**: Delete `token.json` and re-run to trigger fresh browser auth.
- **Emails landing in spam**: Check that the Gmail account has a good sending reputation. Consider sending in smaller batches with longer delays.
