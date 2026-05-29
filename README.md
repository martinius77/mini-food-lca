# Mini Food LCA

A small web tool that compares the **carbon, water, and land-use footprint** of two
food items side by side — with a "this is like driving X km" line to make the numbers
graspable. Region-aware on origins, honest about uncertainty, and available in English
and German without configuration.

It's a single, mobile-first page that updates live: changing any control re-fetches
server-rendered result cards and swaps them in. All calculation stays in Python — the
browser never does footprint math — so the page requires JavaScript by design.

Built as a 2-day learning project. See [PRD.md](PRD.md) for the full spec.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```

To preview a specific country's experience locally (no IP header in dev), append
`?country=AT` (German + EU origins) or `?country=US` (English + Americas origins) to
the home URL. In production, Vercel's `x-vercel-ip-country` header drives this.

## Test

```bash
pip install pytest
python -m pytest tests/ -q
```

The tests map directly to the PRD acceptance criteria (F1–F7).

## How it works

- **System boundary:** cradle-to-gate (production) **plus** a transport leg from the
  selected origin to the user's country. No use phase, no end-of-life.
- **Footprint** = production factor × mass + transport (mode factor × distance × mass).
  Water and land use are production-only; transport adds to carbon only.
- **Transport mode** is chosen by distance: ≤300 km truck, ≤2000 km rail, otherwise sea
  freight — except perishable goods on long hauls, which are flagged as air freight.
- **Distances** are great-circle (haversine) estimates between origin and destination
  centroids stored in `data/origins.csv` — no live API.
- **Uncertainty:** every number is shown with a ±30% band, reflecting typical spread in
  the source data.

## Project layout

```
app.py                  Flask routes: / , /compare/live , /api/health
src/lca.py              calculate_footprint() + compare()
src/transport.py        haversine distance, mode selection, transport emissions
src/comparisons.py      "that's like ..." benchmark picker
src/data_loader.py      cached CSV/JSON loading
data/                   food factors, origins, transport factors, EN/DE strings
templates/ , static/    server-rendered HTML + Apple-style CSS + live-update JS
vercel.json             Python serverless config
```

## Data & honesty

Production factors are **representative values** drawn from the Poore & Nemecek (2018)
meta-study (via Our World in Data). Transport factors are standard mode-based emission
factors. These are ballpark figures for comparison, **not precise measurements** — the
±30% band and the footer say so plainly. Some water-footprint figures come from broader
literature rather than the P&N freshwater-withdrawal column; treat the water column as
the roughest of the three.

## Out of scope (v1)

Accounts, saved comparisons, multi-ingredient meals, >2 items, languages beyond DE/EN,
organic vs conventional, seasonality, packaging, cooking energy, food waste, free-text
food input. See the PRD roadmap for what comes next.
