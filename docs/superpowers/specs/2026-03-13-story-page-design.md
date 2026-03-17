# Story Page Design Spec

## What This Is

A scroll-driven story page that tells the narrative of how Garron converted his mom's dead event decoration inventory into cash using Claude Code. Deployed as a live URL for sharing on Twitter/LinkedIn.

**Audience:** Non-developers, small business owners. The story is the star — the app proves it's real.

**Narrative:** Son helps mom. Organized a warehouse. Knew nothing about the industry. Built an AI-powered lead gen pipeline with Claude Code on a near-zero budget. Found buyers, sent outreach, AI handled replies. Sale coming.

---

## Page Structure

Single-page, vertical scroll. Each section fills the viewport and reveals as you scroll down.

### Hero
- **Headline:** "Turning Dead Inventory Into Cash With Claude Code"
- **Subtext:** "No industry contacts. No industry expertise. And a shoestring budget. Built an outbound lead-gen system in a single afternoon for a fraction of the cost of something like apollo.io or hunter.io"
- Dark cinematic background (gradient #1a1a2e → #16213e)
- "↓ Scroll to see how" prompt

### Chapter 1: The Problem
- **Layout:** Side-by-side — warehouse photos/videos (left) + story text (right)
- **Content:** Mom's event decoration business closing after 20+ years. Warehouse in Manchester, VT. High-end inventory (Jamali Garden, Accent Decor). $100K+ replacement value. Liquidation companies wanted most of the value as their cut.
- But the harder problem: zero records. No master inventory list. No SKUs. No product descriptions. No quantities. No photos. Hundreds of unmarked boxes stacked floor to ceiling. A 20-year business with nothing written down.
- Garron documented the cleanup on TikTok — time-lapse videos, nights and weekends, unpacking and sorting alone.
- **Visual assets:** Real warehouse/inventory photos + embedded TikTok time-lapse videos (3 videos showing the organization phase). Embedded via TikTok oEmbed API as playable iframes. Fallback: thumbnail images linking out to TikTok if embed script causes performance issues.
- **Framing:** This looked like more trouble than it was worth. Liquidation companies saw the chaos and priced accordingly.

### Chapter 2: One Person. Shoestring Budget. Three AI Tools.
- **Layout:** Full-width, dark background — this is the pivot point of the story
- **Content:** Before finding a single buyer, the inventory had to be identified, catalogued, and priced. Garron had no industry knowledge. Didn't know a votive from a candle holder. He also had no money. He was doing this for free to help his mom. so Hiring professionals (like liquidators and appraisers) was out of the question. he wanted to keep it lean so that he could put more cash in his mom's pocket. So he turned to AI. three AI tools replaced three professionals — each one handling a job that used to require hiring out.
- **Visual:** Three-column layout, each column = one phase

| Phase | Tool | Replaced |
|---|---|---|
| Liquidation strategy | Claude (chatbot) | Inventory liquidation consultant |
| Item ID + pricing | Claude Vision + Gemini Vision | Professional appraiser |
| Lead gen + outreach | Claude Code | Lead gen agency |

- **Closing line:** "Nights and weekends. No team. Shoestring budget. Just the right tools."

### Chapter 3: Finding Buyers I Didn't Know Existed
- **Content:** Built an AI pipeline to scrape The Knot marketplace. Found wedding venues and florists across the Northeast.
- **Stats (large numbers):**
  - 727 Qualified Leads
  - 4 Cities Covered
  - $4.38 Total Cost
- **Cities listed:** Boston, New York, Albany Capital Region, Hudson Valley

### Chapter 4: The Bounce Problem (and a $0 Fix)
- **Content:** First batch had too many bounces. Professional tools (Apollo.io) cost money. Built a DIY verification system instead.
- **Visual:** 3-step flow diagram
  - Step 1: Check MX records → "Does this domain accept mail?"
  - Step 2: SMTP handshake → "Does this mailbox exist?"
  - Result: Send or skip → "Zero bounces after this"
- **Punchline:** "Cost: $0. No third-party tools needed."
- Light background (#fafbfc) to differentiate from adjacent sections

### Chapter 5: Reaching Out at Scale
- **Content:** Each email verified before sending. Personal tone, not spam.
- **Email preview:** Styled block showing actual subject line and opening of the email template
- **Stats:**
  - 362 Emails Sent
  - 0 Errors

### Chapter 6: AI Handles the Replies
- **Content:** AI monitor runs daily, classifying responses and drafting replies automatically.
- **Visual:** Classification flow showing three reply types:
  - Interested → AI drafts follow-up with inventory details
  - Decline → Logged, no follow-up
  - Neutral → AI drafts a gentle nudge
- Light background (#fafbfc)

### Chapter 7: Where Things Stand
- **Stats:**
  - 2 Interested Buyers
  - 3 Considering
  - 9 Total Replies
- **Subtext:** "Pipeline still running. Adding more cities. Sale coming soon."

### Closing / Takeaway
- Dark cinematic background matching hero
- **Text:** "With no industry knowledge and $4.38 in API costs, I built a system that found 727 potential buyers and reached 362 of them — cutting out the middleman entirely."
- **Attribution:** "Built by Garron Ware · Powered by Claude Code"

---

## Design Principles

- **Lots of whitespace** — clean, not busy
- **Large stat numbers** — the data tells the story at a glance
- **Real photos** — warehouse/inventory photos featured prominently
- **Scroll animations** — sections fade/slide into view as user scrolls
- **Mobile-first** — must look great on phones (social media traffic)
- **Dark hero/footer, light middle** — cinematic bookends with clean readable content

---

## Technical Architecture

### Stack
- **Astro** — static site generator (lightweight, fast, free deployment)
- **Vanilla CSS** — no framework needed for a single scroll page
- **Intersection Observer** — for scroll-triggered animations

### Data Pipeline
- A Python build script (`tools/build_site_data.py`) reads existing data files:
  - `.tmp/qualified_leads.json` → lead counts, city coverage, unique cities
  - `.tmp/reply_monitor_log.json` → reply stats and classifications (categories: interested, decline, neutral)
  - Google Sheets API (via `tools/sheets_tracker.py`) → email send counts
- Outputs `site/src/data/stats.json` consumed by the Astro build
- **Fallback:** If Google Sheets API fails (expired token, network), the build script falls back to a cached copy of `stats.json` from the last successful run and prints a warning. The site always builds.
- When the pipeline runs again (e.g., adding Philadelphia), re-run the build script and redeploy

### Reply Classification Mapping
The 9 total replies break down as: 2 interested, 3 neutral/considering, 4 declined (mapped from `reply_monitor_log.json` categories). The build script maps the `category` field in each log entry to these three buckets for the Chapter 7 stats.

### Data Files (existing, to be reused)
- `.tmp/qualified_leads.json` — 727 leads with city, buyer_profile, sources
- `.tmp/reply_monitor_log.json` — 9 reply records with category field
- `inventory_liquidation_email_template.md` — the actual email template for preview (show subject line + first 2-3 sentences, truncated with "...")
- `tools/sheets_tracker.py` — existing Google Sheets integration (reuse for send counts)

### Deployment
- **Vercel** — free tier, deploys from git push via `vercel` CLI or GitHub integration
- Static output — no server, no credentials exposed
- Custom domain optional (can use default *.vercel.app URL)

### Directory Structure
```
site/
├── src/
│   ├── pages/
│   │   └── index.astro        # Single page with all chapters
│   ├── components/
│   │   ├── Hero.astro
│   │   ├── Chapter.astro       # Reusable chapter wrapper (number, title, bg)
│   │   ├── StatCard.astro      # Reusable big-number stat block
│   │   ├── EmailPreview.astro
│   │   ├── TikTokEmbed.astro   # TikTok video embed (iframe w/ fallback)
│   │   └── ToolComparison.astro # Ch2 three-column AI tools table
│   ├── layouts/
│   │   └── Layout.astro        # Base HTML shell
│   ├── styles/
│   │   └── global.css          # All styles (vanilla CSS)
│   └── data/
│       └── stats.json          # Generated by build_site_data.py
├── public/
│   └── images/                 # Warehouse/inventory photos
├── astro.config.mjs
└── package.json
```

### Photo Assets
- Garron provides warehouse/inventory photos before implementation begins
- Stored in `site/public/images/`
- Optimized during build (Astro handles image optimization)
- **If photos are not yet available:** Use placeholder blocks with a note "Photo coming" — layout is implemented regardless

### Typography & Animations
- **Font:** System font stack for body (`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`), with a serif accent for the email preview (`Georgia, serif`)
- **Scroll animations:** All chapters use a consistent fade-up (opacity 0→1, translateY 30px→0) triggered by Intersection Observer. No per-section variation — keep it simple.

---

## What's NOT in Scope

- No interactive pipeline demo (visitor can't run the tools)
- No login/auth
- No real-time data (static build, updated manually after pipeline runs)
- No app store deployment
- No exposed API keys or credentials

---

## Verification

1. `npm run build` produces a static site in `dist/`
2. `npm run preview` serves locally — all sections render, scroll animations work
3. Stats in the page match current `.tmp/*.json` data
4. Mobile responsive — test at 375px width (manual browser check)
5. Deploy to Vercel — live URL accessible, no errors
6. Visual spot-check each section in browser (manual QA, no automation needed)
