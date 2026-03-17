# Inventory Liquidation — Project Plan

---

## How We Work Together

### After each step
Stop after completing each step and wait for my confirmation before moving to the next step. Show me what you built and how to verify it works. When I confirm that it works, update `plan.md` to mark the step as complete and note any deviations or issues. Do not proceed to the next step until I give you permission.

### After each session
Update `plan.md` with the progress made over the entire session. Mark completed steps with ✅ and note anything that deviated from the plan or any issues encountered during the session.

### Before starting a new session
Read `plan.md`. Continue from where we left off.

---

# Part 2: Story Page (Shareable Frontend)

## Context

The outreach pipeline (Part 1) is complete and working. Now we need a shareable frontend — a scroll-driven story page deployed to a live URL — so Garron can share the project on Twitter/LinkedIn. The audience is non-developers and small business owners. The story is the star; the app proves it's real.

**Design spec:** `docs/superpowers/specs/2026-03-13-story-page-design.md`

**Narrative:** Son helps mom. Organized a warehouse. Knew nothing about the industry. Built an AI-powered lead gen pipeline with Claude Code on a near-zero budget. Found buyers, sent outreach, AI handled replies. Sale coming.

### Session Log

**Session 1 (2026-03-13):** Brainstormed the design (scroll-driven story page), wrote design spec, wrote implementation plan, created `tools/build_site_data.py`, fixed broken venv (rebuilt with Python 3.14.3), initialized Astro project, installed deps. Steps 1-2 complete. Next: Step 3 (Layout + global styles).

**Session 2 (2026-03-17):** Built entire frontend — layout, styles, all 6 chapters + hero + closing, TikTok embeds, warehouse photos. Garron iteratively refined copy directly in `index.astro` and the design spec. Production build passes, mobile responsive verified at 375px via Playwright. Deployed to Vercel, renamed project from `007_cold-outreach-inference-response` to `007-cold-outreach-inference-response`, fixed domain to `007-cold-outreach-inference-response.vercel.app`. All steps complete.

## Step 1: Fix Python venv + Create data build script ✅

**Status:** Complete

**What was done:**
- `tools/build_site_data.py` created — reads `.tmp/*.json` + Google Sheets → outputs `site/src/data/stats.json`
- Venv recreated with Python 3.14.3 (via `/opt/homebrew/bin/python3`)
- `build_site_data.py` runs successfully, `stats.json` generated with correct data

**Deviations:**
- Original venv had broken symlinks pointing to old CloudDocs path — had to recreate from scratch
- Initially recreated with system Python 3.9, then rebuilt with Homebrew Python 3.14.3
- Google Sheets token is expired, so the build script used the fallback (cached value of 362 emails sent). Fallback mechanism worked as designed.

## Step 2: Initialize Astro project ✅

**Status:** Complete

**What was done:**
- Astro project scaffolded in `site/` with minimal template
- npm dependencies installed (248 packages, 0 vulnerabilities)
- `site/src/data/stats.json` generated and in place

## Step 3: Base layout + global styles ✅

**Status:** Complete

**What was done:**
- `site/src/layouts/Layout.astro` — HTML shell with OG/Twitter Card meta tags, TikTok embed script
- `site/src/styles/global.css` — design tokens, CSS reset, section layout (dark/light), stat cards, two-column layout, flow diagram, email preview, classification badges, photo grid, TikTok row, scroll animations, responsive breakpoints
- OG image placeholder (og.png not yet created — uses placeholder URL)

## Step 4: Build reusable components ✅

**Status:** Complete

**Deviations:**
- Did NOT create separate `.astro` component files. All components are built inline in `index.astro` with CSS classes in `global.css`. This is simpler for a single-page site — no need for the abstraction of separate component files when there's only one page consuming them.

## Step 5: Assemble index.astro ✅

**Status:** Complete

**What was done:**
- Full page assembled in `site/src/pages/index.astro` with all sections
- Intersection Observer script for scroll fade-up animations
- Stats pulled from `stats.json` (727 leads, 4 cities, $4.38, 362 emails, 9 replies)

**Deviations from original plan:**
- 6 chapters (not 7) — the "Three AI Tools" chapter from the design spec was removed during brainstorming
- Chapter structure: Hero → Ch1 The Problem → Ch2 Finding Buyers → Ch3 Bounce Problem → Ch4 Reaching Out → Ch5 AI Replies → Ch6 Where Things Stand → Closing → TikTok Videos
- TikTok videos placed at the bottom as a horizontal row (not in Ch1 as originally spec'd)
- 6 warehouse photos added to Ch1 as a 2x3 grid (left side of two-column layout)
- Garron edited copy directly throughout the session — hero headline, hero subtext, chapter body text, email preview text all refined from original spec/brainstorm versions
- TikTok short URLs required resolution via oEmbed API to get actual video IDs

## Step 6: Local build + test ✅

**Status:** Complete

- [x] `cd site && npm run build` succeeds (575ms, 0 errors)
- [x] All sections render, scroll animations work
- [x] Mobile responsive at 375px width (verified via Playwright)
- [x] TikTok embeds load (all 3 videos render)
- [ ] `python tools/build_site_data.py` — not re-run this session (using existing stats.json)

## Step 7: Deploy to Vercel ✅

**Status:** Complete

**What was done:**
- Committed and pushed all site code to GitHub (`garronware/007_cold-outreach-inference-response`)
- Deployed to Vercel via CLI (`vercel --prod` from project root)
- Renamed Vercel project from `007_cold-outreach-inference-response` to `007-cold-outreach-inference-response` via REST API
- Fixed production domain from `007cold-outreach-inference-response.vercel.app` to `007-cold-outreach-inference-response.vercel.app` (added as project domain via API, removed old one)
- Verified live site via Playwright — all sections render, TikTok embeds load
- Deleted accidental "site" project created during first deploy attempt

**Deviations:**
- First deploy from `site/` directory created an accidental separate "site" project on Vercel — had to delete it, then link and deploy from the project root instead
- Vercel auto-generated domain stripped underscores from project name, producing `007cold-outreach-inference-response.vercel.app` (missing hyphen). Had to manually add the correct domain via `/v10/projects/.../domains` API and remove the old one
- `vercel alias set` alone was insufficient — it created a deployment alias behind SSO protection. Adding the domain as a proper project domain via the API was the fix

**Live URL:** https://007-cold-outreach-inference-response.vercel.app

- [x] Deployed to Vercel via CLI
- [x] Live URL works, all content renders
- [x] Verified via Playwright browser check

## Assets needed from Garron

- [x] 3 TikTok video URLs → `media-assets/tiktok-urls.md` (resolved via oEmbed API to full video IDs)
- [x] Warehouse/inventory photos → `site/public/images/` (6 photos added, no before/after split — all "after")

---

# Part 1: Outreach Pipeline (Complete)

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
