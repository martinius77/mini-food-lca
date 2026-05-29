# Mini-Food-LCA — PRD v1

## What it is

A web tool that compares the carbon, water, and land-use footprint of two food items side by side. Built for a non-expert (mother in Austria, German-speaking) and a credibility-focused friend (California, English-speaking). Learning project, 2-day build, not a startup.

## North star

Most food carbon tools give you a single confusing number. This one gives you two foods next to each other with a "this is like driving X minutes" comparison anyone can grasp. Honest about uncertainty, region-aware on origins, available in the user's language without configuration.

## Users & success

- **Mom (Austria, DE).** Wins when she compares two things she's about to buy and gets a surprise — e.g. discovers local cheese is worse than imported strawberries. Needs German UI, EU origin options, food names she recognizes.
- **Friend (California, EN).** Wins when the link loads cleanly on his phone, looks polished (Apple-style), and the methodology reads as honest. Won't be a power user.

## Scope (v1)

- **Functional unit:** per item or per gram, user-selected (e.g. "one banana" or "100g chicken").
- **System boundary:** cradle-to-gate, with transport from origin to user's country added on top. No use phase, no end-of-life.
- **Impact categories:** carbon (kg CO2e), water (litres), land use (m²). All three displayed in results.

## Features

### F1. Two-item comparison
User selects food A and food B from a ~40-item dropdown, enters quantity, picks origin from a region-filtered dropdown. Hits Compare.

- **Test:** comparing identical items in identical quantities returns identical results.
- **Test:** changing food B updates only food B's numbers and the delta.

### F2. ~40-food library
Covers a real grocery list: produce, proteins, dairy, grains, oils. Fixed dropdown, no free text in v1.

- **Test:** every food has carbon + water + land-use factors loaded.

### F3. Origin selection (region-filtered)
User's region (detected by IP) determines which origin countries appear. EU users see ~15 EU + nearby origins. US users see ~15 Americas origins. Plus a "don't know / average" fallback.

- **Test:** an Austrian IP shows Spain, Morocco, Netherlands etc.; a California IP shows Mexico, Peru, US states.

### F4. Transport-aware calculation
Final footprint = production factor (per kg) × quantity + transport factor (kg CO2e per km × distance × mode). Mode defaults: <300 km truck, 300-2000 km truck/rail, >2000 km sea freight (or air for highly perishable items like berries, flagged in UI).

- **Test:** banana from Ecuador to Austria > banana from Spain to Austria.

### F5. Relatable comparisons
Every result includes a "this is like…" line picked from a small benchmark list (driving X km, Y bottles of water, Z phone charges, etc.), scaled to be in a relatable range for the magnitude.

- **Test:** a 0.1 kg CO2e result picks a different benchmark than a 10 kg CO2e result.

### F6. Light uncertainty display
Each number shows ± a range. Footnote explains: "Estimates have a typical uncertainty of ±30% based on source data."

- **Test:** every displayed value has a ± component.

### F7. Auto-language with override
IP geolocation detects country → defaults to German (Austria, Germany, Switzerland) or English (everywhere else). EN/DE toggle visible in corner. First-load banner: "Detected: Austria, German. Change?"

- **Test:** an Austrian IP loads in German.
- **Test:** clicking the toggle persists the choice for the session.

## Data sources

- **Production factors (carbon, water, land use):** Poore & Nemecek 2018 meta-study, available as CSV from Our World in Data.
- **Transport factors:** standard mode-based emission factors (sea freight ~0.01 kg CO2e/tonne-km, truck ~0.1, air ~0.6). Cited in footer.
- **Origin → user country distances:** precomputed lookup table (no live API).

## UI / design

Apple-style. White space, big numbers, system font (San Francisco / system-ui fallback), minimal color. Two columns for comparison. Hotspot breakdown bar under each total. Light + dark mode optional, not required.

## Tech

- **Backend:** Python + Flask.
- **Frontend:** server-rendered HTML + minimal CSS (no React, no build step).
- **Hosting:** Vercel (Python serverless), connected to GitHub for auto-deploy.
- **Geolocation:** free IP-to-country service (e.g. ipapi.co free tier, or Vercel's built-in `x-vercel-ip-country` header — the latter is free, fast, and doesn't need an API key).
- **Language:** simple dict-based string lookup, EN + DE only.

## Explicitly out of scope (v1)

User accounts, saved comparisons, recipes, multi-ingredient meals, history/tracking, more than 2 items, languages beyond DE/EN, organic vs conventional, seasonality, biodiversity impact, packaging, cooking energy, food waste, free-text food input, more granular origin (within-country regions), production-method differences (greenhouse vs field).

## Roadmap (not v1)

- **v1.5:** add seasonality (greenhouse/air-freight flag for off-season produce in user's region)
- **v2:** organic vs conventional toggle (when better data is sourced)
- **v3:** more languages (FR, ES)
- **v4:** biodiversity impact category

## Build plan for Claude Code (hand off after PRD approval)

1. Add `data/food_factors.csv` with ~40 foods × (carbon, water, land use) from Poore & Nemecek
2. Add `data/origins.csv` (country, lat/lon, region grouping)
3. Add `data/transport_factors.csv` (mode, kg CO2e per tonne-km)
4. Add `data/translations.json` (EN + DE strings)
5. Extend `src/lca.py` with: `calculate_footprint(food, quantity, origin, user_country)` returning carbon + water + land use, each as `{value, lower, upper}`
6. Add `src/transport.py` with distance lookup + mode selection
7. Add `src/comparisons.py` with the "this is like…" benchmark picker
8. Add `app.py` with Flask routes: `/` (form), `/compare` (POST → results), `/api/health` (deploy check)
9. Add `templates/` with `index.html` and `result.html`, Apple-style CSS in `static/style.css`
10. Add `vercel.json` config for Python serverless
11. Test locally with `flask run`, then push to GitHub and confirm Vercel deploy
