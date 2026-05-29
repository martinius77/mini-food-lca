"""Mini Food LCA — Flask app.

Routes:
  GET  /            comparison form (region-filtered origins, auto-language)
  POST /compare     results for two food selections
  GET  /api/health  deploy check

Language is auto-detected from the visitor's country (Vercel's
``x-vercel-ip-country`` header) and can be overridden via the corner toggle,
which persists for the session.
"""

import os

from flask import Flask, redirect, render_template, request, session, url_for

from src.data_loader import load_foods, load_origins, load_transport_factors, load_translations
from src.lca import compare
from src.transport import AVERAGE_ORIGIN

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

SUPPORTED_LANGS = ("en", "de")
# Countries that default to German.
GERMAN_COUNTRIES = {"AT", "DE", "CH"}
# Country fallback when no IP header is present (local dev). Override via env.
DEFAULT_COUNTRY = os.environ.get("DEFAULT_COUNTRY", "AT")

# Country codes whose visitors see the EU origin list; everything else => Americas.
EU_REGION_COUNTRIES = {
    "AT", "DE", "CH", "ES", "IT", "NL", "FR", "PL", "GR", "GB", "IE", "BE",
    "PT", "SE", "NO", "DK", "FI", "CZ", "SK", "HU", "RO", "BG", "HR", "SI",
    "LU", "EE", "LV", "LT", "MA", "TR", "EG", "IL",
}


# --- request context helpers -------------------------------------------------

def detect_country():
    """Visitor country code: Vercel IP header, ?country= override, or default."""
    header = request.headers.get("x-vercel-ip-country")
    override = request.args.get("country")
    return (header or override or DEFAULT_COUNTRY).upper()


def language_for_country(country):
    return "de" if country in GERMAN_COUNTRIES else "en"


def current_language(country):
    """Session override wins; otherwise derive from the detected country."""
    chosen = session.get("lang")
    if chosen in SUPPORTED_LANGS:
        return chosen
    return language_for_country(country)


def region_for_country(country):
    return "eu" if country in EU_REGION_COUNTRIES else "americas"


# --- view-model builders -----------------------------------------------------

def localized_foods(lang):
    """Food list sorted by localized name for the dropdowns."""
    foods = load_foods().values()
    items = [{"id": f["id"], "name": f["name_" + lang], "category": f["category"]} for f in foods]
    return sorted(items, key=lambda f: f["name"].lower())


def localized_origins(lang, region):
    """Region-filtered origin list + the 'average / don't know' fallback."""
    origins = [o for o in load_origins().values() if region in o["regions"]]
    items = [{"id": o["id"], "name": o["name_" + lang]} for o in origins]
    items.sort(key=lambda o: o["name"].lower())
    t = load_translations()[lang]
    items.append({"id": AVERAGE_ORIGIN, "name": t["origin_average"]})
    return items


def fmt_number(value, lang, decimals=None):
    """Format a number, choosing decimals by magnitude; comma decimals for German."""
    if decimals is None:
        if value < 1:
            decimals = 2
        elif value < 10:
            decimals = 1
        else:
            decimals = 0
    text = f"{value:,.{decimals}f}"
    if lang == "de":
        # German conventions: '.' for thousands, ',' for decimals. Swap both
        # separators in a single pass so neither clobbers the other.
        text = text.translate({ord(","): ".", ord("."): ","})
    return text


def build_card(result, food_id, origin_id, lang):
    """Turn a calculate_footprint result into a template-ready card."""
    t = load_translations()[lang]
    food = load_foods()[food_id]
    origins = load_origins()

    origin_name = (
        t["origin_average"] if origin_id == AVERAGE_ORIGIN else origins[origin_id]["name_" + lang]
    )

    # Transport line.
    mode = result["transport_mode"]
    if mode:
        mode_name = load_transport_factors()[mode]["name_" + lang]
        transport_line = t["transport_via"].format(mode=mode_name)
    else:
        transport_line = None

    # Benchmark line.
    benchmark = result["benchmark"]
    if benchmark:
        n_text = fmt_number(benchmark["n"], lang)
        benchmark_text = t[benchmark["key"]].format(n=n_text)
    else:
        benchmark_text = None

    return {
        "name": food["name_" + lang],
        "origin_name": origin_name,
        "carbon": result["carbon"],
        "water": result["water"],
        "land": result["land"],
        "breakdown": result["carbon_breakdown"],
        "transport_line": transport_line,
        "air_flagged": result["air_flagged"],
        "benchmark_text": benchmark_text,
    }


def delta_text(delta_pct, other_name, lang):
    t = load_translations()[lang]
    if abs(delta_pct) < 5:
        return t["delta_same"].format(other=other_name)
    key = "delta_more" if delta_pct > 0 else "delta_less"
    return t[key].format(pct=abs(round(delta_pct)), other=other_name)


# --- routes ------------------------------------------------------------------

@app.context_processor
def inject_globals():
    """Expose the number formatter to all templates."""
    return {"fmt": fmt_number}


@app.route("/lang/<lang>")
def set_language(lang):
    """Persist a language override for the session, then go home."""
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
    return redirect(url_for("index"))


@app.route("/")
def index():
    country = detect_country()
    lang = current_language(country)
    region = region_for_country(country)
    t = load_translations()[lang]
    translations = load_translations()

    other_lang = "de" if lang == "en" else "en"
    country_names = translations["countries"].get(country, {})
    country_label = country_names.get(lang, country)
    banner = t["detect_banner"].format(country=country_label, language=t["lang_name"])

    return render_template(
        "index.html",
        t=t,
        lang=lang,
        foods=localized_foods(lang),
        origins=localized_origins(lang, region),
        units=[("item", t["unit_item"]), ("grams", t["unit_grams"])],
        banner=banner,
        other_lang=other_lang,
        other_lang_name=translations[other_lang]["lang_name"],
        show_toggle_banner=session.get("lang") is None,
    )


# Defaults so a selection is always valid even with missing/empty params.
DEFAULT_FOODS = {"a": "beef", "b": "tofu"}


def comparison_context(getter, country, lang):
    """Run the two-food comparison and return the template context for _cards.html.

    ``getter`` is a ``request.args.get``-style callable so the same logic serves
    any source of form values. All math, formatting and uncertainty stay in
    Python; the caller only renders the result.
    """
    def selection(side):
        try:
            quantity = float(getter("qty_" + side, "1") or 1)
        except ValueError:
            quantity = 1.0
        return {
            "food_id": getter("food_" + side) or DEFAULT_FOODS[side],
            "quantity": quantity,
            "origin": getter("origin_" + side) or AVERAGE_ORIGIN,
            "user_country": country,
            "unit": getter("unit_" + side) or "item",
        }

    sel_a = selection("a")
    sel_b = selection("b")
    result = compare(sel_a, sel_b)

    card_a = build_card(result["a"], sel_a["food_id"], sel_a["origin"], lang)
    card_b = build_card(result["b"], sel_b["food_id"], sel_b["origin"], lang)

    return {
        "t": load_translations()[lang],
        "lang": lang,
        "card_a": card_a,
        "card_b": card_b,
        "delta": delta_text(result["delta_pct"], card_a["name"], lang),
    }


@app.route("/compare/live")
def compare_live():
    """Render ONLY the cards fragment from query-string selections (for fetch)."""
    country = detect_country()
    lang = current_language(country)
    context = comparison_context(request.args.get, country, lang)
    return render_template("_cards.html", **context)


@app.route("/api/health")
def health():
    return {"status": "ok", "foods": len(load_foods()), "origins": len(load_origins())}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
