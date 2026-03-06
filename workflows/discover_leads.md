# Discover Leads Workflow

## Objective
Find potential buyers for inventory liquidation using Google Places API and The Knot scraper.

## Tools
- `tools/discover_google_places.py` — Google Places API (New) Text Search
- `tools/discover_theknot.py` — Apify scraper for The Knot marketplace

## Google Places Discovery

### Run Commands

**Test run (1 city, 1 profile):**
```bash
source venv/bin/activate
python tools/discover_google_places.py wedding_venues "Boston, MA"
```

**Full run (all profiles, all cities):**
```bash
source venv/bin/activate
python tools/discover_google_places.py
```

**Single profile, all cities:**
```bash
source venv/bin/activate
python tools/discover_google_places.py wedding_venues
python tools/discover_google_places.py floral_designers
```

### Search Configuration

Defined in `tools/discover_google_places.py` SEARCHES dict:

| Profile | Queries | Cities |
|---------|---------|--------|
| wedding_venues | "wedding venue", "wedding reception venue", "event venue weddings" | 15 cities |
| floral_designers | "wedding florist", "event florist", "floral designer" | 11 cities |

### Output
- File: `.tmp/raw_leads_places.json`
- Deduplicated by `place_id`
- Fields: name, address, rating, review_count, website, price_level, phone, types

### Cost Estimate
- ~$17 per 1,000 results
- Full run (all profiles, all cities): ~500-800 unique results = ~$8-14
- Each search query+city combo returns up to 40 results (2 pages of 20)

### Rate Limits
- 0.3s delay between searches
- 0.5s delay between pages
- No known hard rate limit for Places API (New), but be reasonable

## The Knot Discovery

### Run Commands

**Test run (1 category, 1 city):**
```bash
source venv/bin/activate
python tools/discover_theknot.py venues boston
```

**Full run (all categories, all cities):**
```bash
source venv/bin/activate
python tools/discover_theknot.py
```

**Single category, all cities:**
```bash
source venv/bin/activate
python tools/discover_theknot.py venues
python tools/discover_theknot.py florists
```

### Search Configuration

Defined in `tools/discover_theknot.py` SEARCHES dict:

| Category | URL Pattern | Cities | Max Pages |
|----------|-------------|--------|-----------|
| venues | wedding-reception-venues | 15 cities | 5 |
| florists | wedding-florists | 11 cities | 5 |

### Output
- File: `.tmp/raw_leads_theknot.json`
- Deduplicated by name + location
- Fields: name, location, rating, review_count, price_range, capacity, website, phone, email, description

### Cost Estimate
- ~$6.90 per 1,000 results
- Boston test (5 pages): 145 results
- Full run estimate: ~1,500-3,000 results across all cities = ~$10-21

### Batching
- Apify limits to 4 URLs per actor run
- Tool automatically batches URLs in groups of 4

## Lessons Learned
- Google Places dedup is important: 3 queries per city produces ~50% overlap
- `price_level` field is often empty for venues — `review_count` is the better size proxy
- Most Google Places results have websites (96%+), which is critical for Apollo enrichment later
- The Knot data is very rich: 100% email and website coverage in test runs
- The Knot provides direct email addresses, reducing need for Apollo enrichment on those leads
- Correct The Knot URL format: `wedding-reception-venues` not `wedding-venues`
