# Progress Report — Inventory Liquidation Workflow Automation
**Updated:** 2026-02-26 (Session 2)

## What's Been Built (6 of 8 tools complete)

### Completed Tools
1. **`tools/discover_google_places.py`** — Google Places API Text Search discovery
   - RETIRED: Google Places is no longer used. The Knot is the sole discovery source.
   - Reason: Google Places doesn't return email addresses, making leads useless without enrichment.

2. **`tools/discover_theknot.py`** — Apify-powered The Knot marketplace scraper
   - Primary discovery tool. Returns 100% email coverage.
   - Categories: `venues` (wedding-reception-venues) and `florists` (florists)
   - Bug fix (Session 2): florist URL slug changed from `wedding-florists` to `florists`
   - Now merges with existing data on re-run (won't overwrite prior results)
   - Output: `.tmp/raw_leads_theknot.json`

3. **`tools/qualify_leads.py`** — Merge, deduplicate, and filter leads
   - Merges both sources, matches by name + domain
   - Current totals: 471 qualified leads
   - Output: `.tmp/qualified_leads.json`

4. **`tools/sheets_tracker.py`** — Google Sheets CRM
   - Creates spreadsheet, imports leads, tracks email status
   - Live sheet: https://docs.google.com/spreadsheets/d/1GrXh-bEPxplORdhy7yQPLsnqs-RPQ9F27PawN_ggkhA/edit
   - Commands: `create`, `import`, `status`, `update`

5. **`tools/google_auth_helper.py`** — Shared OAuth2 helper
   - Used by Sheets tracker and Gmail sender
   - Token cached in `token.json` after first browser auth
   - Scopes: gmail.send + spreadsheets

6. **`tools/send_gmail.py`** — Gmail API email sender (NEW — Session 2)
   - Reads unsent leads from Google Sheet, sends HTML email, updates Sheet
   - Converts markdown template to HTML (uses `markdown` Python package)
   - CLI: `--dry-run`, `--send`, `--to`, `--limit`, `--delay`
   - Safety: dry-run by default, must pass `--send` to deliver
   - Template: `inventory_liquidation_email_template.md` (universal, no per-recipient variables)

### Completed Workflows
- `workflows/discover_leads.md` — Run commands, config, cost estimates, lessons learned
- `workflows/qualify_leads.md` — Filter thresholds, dedup logic, stats
- `workflows/send_outreach.md` — Send commands, testing steps, troubleshooting (NEW — Session 2)

### Not Yet Built (deprioritized)
7. **`tools/enrich_apollo.py`** — Apollo.io Search API (90 credits available)
8. **`tools/enrich_hunter.py`** — Hunter.io backup (50 credits available)

Enrichment is deprioritized because The Knot provides 100% email coverage for all leads. These tools are only needed if we want to reach businesses not on The Knot.

## Emails Sent — Session 2

| Batch | Category | Cities | Leads Sent | Errors |
|-------|----------|--------|-----------|--------|
| 1 | Wedding venues | Boston area | 145 | 0 |
| 2 | Florists | Boston + NYC | 217 | 0 |
| **Total** | | | **362** | **0** |

All sends tracked in Google Sheet with date and "sent" status.

## API Costs

| Service | Calls Made | Estimated Cost |
|---------|-----------|---------------|
| Google Places API | 12 requests (Boston + NYC florists) | ~$0.38 |
| Apify (The Knot) | 4 actor runs (venues + florists, Boston + NYC) | ~$4.00 |
| Apollo.io | 0 | $0.00 |
| Hunter.io | 0 | $0.00 |
| Gmail API | 362 sends | Free |
| **Total spent** | | **~$4.38** |

**API Cost Cap: $10 TOTAL.** Remaining: ~$5.62.

## Key Decisions Made — Session 2

1. **Google Places retired.** The Knot is the sole discovery source (provides emails).
2. **Enrichment deprioritized.** With 100% email coverage from The Knot, Apollo/Hunter credits (140 total) are saved for later.
3. **Email template finalized.** Universal template, no per-recipient personalization. Stored at `inventory_liquidation_email_template.md`.
4. **Apollo credits are 90 (not 1,250).** Hunter credits: 50. Total: 140. Test with 1-3 per run if/when we build enrichment.

## Environment Setup

- **Python:** 3.9.6 (via venv at `./venv`)
- **Dependencies:** requests, python-dotenv, google-auth, google-auth-oauthlib, google-api-python-client, markdown
- **OAuth:** Working — token cached in `token.json`
- **All API keys:** In `.env` (standardized to SCREAMING_SNAKE_CASE)

## What to Do Next

1. **Monitor responses** from the 362 emails sent
2. **Expand discovery** to more cities using The Knot scraper (venues + florists)
3. **Build enrichment tools** (Apollo/Hunter) only if needed for non-Knot leads
4. **Follow-up emails** for non-responders (timing TBD)

## Files — Full List

```
tools/
  discover_google_places.py    # Google Places discovery (RETIRED)
  discover_theknot.py          # The Knot/Apify discovery (PRIMARY)
  qualify_leads.py             # Merge + filter leads
  sheets_tracker.py            # Google Sheets CRM
  google_auth_helper.py        # Shared OAuth helper
  send_gmail.py                # Gmail API email sender (NEW)

workflows/
  discover_leads.md            # Discovery workflow docs
  qualify_leads.md             # Qualification workflow docs
  send_outreach.md             # Send workflow docs (NEW)

.tmp/
  raw_leads_places.json        # 191 leads (Google Places — retired source)
  raw_leads_theknot.json       # 381 leads (The Knot — primary source)
  qualified_leads.json         # 471 merged+qualified leads
  email_preview.html           # HTML preview of email template

Other:
  inventory_liquidation_email_template.md  # Finalized email template
  plan.md                      # Full project plan
  venv/                        # Python virtual environment
  token.json                   # Google OAuth cached token
```
