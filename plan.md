# Inventory Liquidation — Workflow Automation Plan

## Context

Helping close a high-end floral/event design studio in southern Vermont. The inventory (~$100K-$150K replacement cost) includes Jamali Garden-style hard goods: vases, pedestals, ribbons, containers, plus custom nature-themed/Vermont items and gardening supplies. Goal is a single-lot sale to one buyer for $30K+ within ~30 days. This automation finds qualified buyers, gets their contact info, and sends personalized outreach emails.

## Decisions Made

- **Priority buyer profiles:** High-Volume Wedding Venues (#2) first, then Floral/Event Designers (#1). Expand to other profiles if needed.
- **Email sending:** Gmail API from personal account
- **Tracking:** Google Sheets as lightweight CRM
- **Email enrichment:** Apollo.io (primary, ~1,250 free trial credits), Hunter.io (backup, 50 free credits)
- **Budget:** Under $50 total for paid APIs
- **Email template:** Based on Template 3 (most polished), with buyer-profile-specific personalization

## API Budget Breakdown (Target: <$50)

| Service | Cost | Credits/Results |
|---------|------|-----------------|
| Apollo.io | Free (14-day trial) | ~1,250 email lookups |
| Hunter.io | Free | 50 email lookups |
| Gmail API | Free | 500 sends/day |
| Google Sheets API | Free | Unlimited |
| Google Places API | ~$17 | 1,000 results |
| Apify (The Knot) | ~$5-7 | 1,000 results |
| **Total** | **~$22-24** | |

## Pipeline Overview

```
DISCOVER → QUALIFY → ENRICH → OUTREACH → TRACK
```

### Step 1: DISCOVER — Build raw lead lists

**Tool: `tools/discover_google_places.py`**
- Uses Google Places API (Text Search)
- Searches by buyer profile + city combinations
- Buyer Profile #2 queries: "wedding venue" in target cities
- Buyer Profile #1 queries: "wedding florist", "event florist", "floral designer" in target cities
- Outputs raw results to `.tmp/raw_leads_places.json`
- Fields captured: name, address, rating, review count, price_level, website, place_id

**Tool: `tools/discover_theknot.py`**
- Uses Apify API to run dionysus_way/the-knot-marketplace-scraper
- Scrapes The Knot for wedding venues and floral designers
- Outputs to `.tmp/raw_leads_theknot.json`
- Fields captured: name, location, category, starting_price, review_count, website

**Workflow: `workflows/discover_leads.md`**
- Defines which cities to search for each profile
- Defines search queries per profile
- Documents API costs and rate limits

### Step 2: QUALIFY — Filter for size/fit

**Tool: `tools/qualify_leads.py`**
- Reads raw lead files from Step 1
- Deduplicates across sources (match on business name + city)
- Applies qualification filters:
  - Wedding venues: review_count >= 200 OR starting_price >= $10,000
  - Floral designers: review_count >= 100 OR price_level >= 3
- Outputs qualified leads to `.tmp/qualified_leads.json`
- Also outputs to Google Sheets for manual review

**Workflow: `workflows/qualify_leads.md`**
- Documents filter thresholds and rationale
- Defines manual review process (user can override filters)

### Step 3: ENRICH — Get contact emails

**Tool: `tools/enrich_apollo.py`**
- Takes qualified leads list (company name + domain)
- Uses Apollo.io **Search API** to find decision-maker contacts
- Searches by company domain + job title filters
- Targets: owner, general manager, event director, creative director
- Outputs enriched leads to `.tmp/enriched_leads.json`
- Tracks credit usage

**Tool: `tools/enrich_hunter.py`** (backup)
- Same flow using Hunter.io API
- Used when Apollo credits run out

**Workflow: `workflows/enrich_contacts.md`**
- Defines which job titles to target per buyer profile
- Documents credit budgeting strategy
- Apollo first (1,250 credits), Hunter backup (50 credits)

### Step 4: OUTREACH — Send personalized emails

**Base template:** Template 3 from user's drafts. Personalization variables:

| Variable | Source |
|----------|--------|
| `[Name]` | Apollo/Hunter enrichment (contact first name) |
| `[company_name]` | Discovery data |
| `[profile_hook]` | Buyer-profile-specific opening line (see below) |
| `[google_drive_link]` | Hardcoded — user's Google Drive photo/video folder |

**Tone: Personal, not salesy.** This is a son helping his mom — not a B2B pitch. The opening
is the same for all buyer profiles. Something like:

> "My mom's floral & event design business is closing. And I'm helping her sell the
> inventory. As I organized for this sale, I realized I'm probably the only guy I know
> who grew up doing homework at a workbench surrounded by 7 ladies making wedding
> bouquets. Anyway..."

User will finalize exact wording. The personal story IS the hook — no profile-specific
sales language needed. The only per-profile variation is which inventory items to
emphasize in the "Collection Includes" section:
- **Floral designers:** Lead with vessels, vases, ribbons, floral supplies
- **Wedding venues:** Lead with centerpieces, ceremony structures, pedestals, votive holders
- **Event rental cos:** Lead with full breadth — vessels, structures, accents, planters
- **Hotels/Resorts:** Lead with pedestals, planters, accent pieces, premium containers
- **Corporate event cos:** Lead with architectural pieces, pedestals, centerpieces

**Subject line:** Personal tone, matching the email body. e.g.:
- "Helping my mom liquidate her floral studio — interested in the inventory?"
- User will finalize exact wording.

**Items to finalize with user before sending:**
- [ ] Fill in bracket placeholders in Template 3 with real inventory counts
- [ ] Confirm Google Drive share link
- [ ] Approve final subject lines

**Tool: `tools/send_gmail.py`**
- Uses Gmail API via OAuth
- Reads enriched leads from `.tmp/enriched_leads.json`
- Renders Template 3 with personalization variables
- Sends in batches with configurable delay (avoid spam flags)
- Logs each send to Google Sheets
- Supports dry-run mode (preview without sending)
- Personalizes "Collection Includes" section based on buyer profile

**Workflow: `workflows/send_outreach.md`**
- Documents email template and all variables
- Defines send cadence (e.g., 50/day across profiles)
- Documents follow-up timing

### Step 5: TRACK — Log and monitor

**Tool: `tools/sheets_tracker.py`**
- Creates/updates a Google Sheet with columns:
  - Company, Contact Name, Email, Buyer Profile, City
  - Discovery Source, Qualification Score
  - Email Sent Date, Email Status, Follow-Up Date
  - Response, Notes
- Provides summary stats (sent, opened, replied)

**Workflow: `workflows/track_responses.md`**
- Defines follow-up cadence
- Documents how to handle responses

## Build Order

| Phase | What to Build | Dependencies |
|-------|--------------|--------------|
| 1 | `tools/discover_google_places.py` + workflow | Google Places API key |
| 2 | `tools/discover_theknot.py` + workflow | Apify API key |
| 3 | `tools/qualify_leads.py` + workflow | Steps 1-2 output |
| 4 | `tools/sheets_tracker.py` | Google Sheets API / OAuth |
| 5 | `tools/enrich_apollo.py` + workflow | Apollo.io API key |
| 6 | `tools/enrich_hunter.py` (backup) | Hunter.io API key |
| 7 | `tools/send_gmail.py` + workflow | Gmail OAuth + templates |

## Verification

- **Step 1:** Run discovery for 1 city, 1 profile. Verify JSON output has expected fields.
- **Step 2:** Run qualification. Verify dedup works and filters remove small businesses.
- **Step 3:** Run enrichment on 5 test leads. Verify emails are returned and credits tracked.
- **Step 4:** Dry-run email send. Verify template renders correctly. Then send 1 real test email to yourself.
- **Step 5:** Verify Google Sheet updates after each step.

## Credentials Status

- [x] Google Places API key → `.env` as `Google_Places_API_Key`
- [x] Apify API key → `.env` (rename var to `APIFY_API_TOKEN` during build)
- [x] Apollo.io Search API key → `.env` as `Apollo_API_Key`
- [x] Hunter.io API key → `.env` as `Hunter_API_Key`
- [x] Gmail OAuth → `gmail-0Auth-credentials.json` in project root
- [x] Google Drive share link → `https://drive.google.com/drive/folders/1oYxSRocMV7Mm--zOW4nqo5nf-QhS2abW?usp=sharing`

## .env Cleanup (during build)

Standardize variable names to SCREAMING_SNAKE_CASE:
- `inventory-liquidation-python` → `APIFY_API_TOKEN`
- `Google_Places_API_Key` → `GOOGLE_PLACES_API_KEY`
- `Hunter_API_Key` → `HUNTER_API_KEY`
- `Apollo_API_Key` → `APOLLO_API_KEY`
- Remove redundant Gmail Client_ID/Client_secret (already in credentials JSON)

## Open Items

- [x] Email template content — Template 3 selected as base
- [ ] Fill in Template 3 bracket placeholders with real inventory counts
- [ ] Target city list finalization per buyer profile
- [ ] Google Sheets spreadsheet creation (will create during build)
