# Qualify Leads Workflow

## Objective
Merge leads from Google Places and The Knot, deduplicate, and filter for businesses large enough to be viable buyers.

## Tool
`tools/qualify_leads.py`

## Run Commands

**Standard run (merge + filter):**
```bash
source venv/bin/activate
python tools/qualify_leads.py
```

**Merge only (no filtering):**
```bash
source venv/bin/activate
python tools/qualify_leads.py --no-filter
```

## Input Files
- `.tmp/raw_leads_places.json` (from Google Places discovery)
- `.tmp/raw_leads_theknot.json` (from The Knot discovery)
- Either or both can exist; tool works with whatever is available

## Output
- `.tmp/qualified_leads.json`
- Sorted by review count (highest first)
- Merged fields from both sources where available

## Deduplication Logic
Matches leads across sources using:
1. Normalized business name (case-insensitive, stripped of LLC/Inc/etc.)
2. Website domain (fallback when names don't match exactly)

## Qualification Filters

| Profile | Min Reviews | Override |
|---------|------------|---------|
| wedding_venues | 50 | Auto-pass if on The Knot or has email |
| floral_designers | 30 | Auto-pass if on The Knot or has email |

The Knot listings auto-qualify because they're established businesses with marketplace profiles.
Leads with direct email addresses also auto-qualify (high-value contact data).

## Lessons Learned
- The Knot data is extremely rich: 100% email coverage in testing
- Cross-source matching found 29 overlaps out of 203 total (Boston test)
- Only ~15% of qualified leads need Apollo enrichment for emails
- This dramatically reduces Apollo credit consumption vs. original estimate
