"""HTTP-level tests for routing, language detection (F7) and origin filtering (F3)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import app


@pytest.fixture
def client():
    return app.test_client()


# F7 — an Austrian IP loads in German.
def test_austrian_ip_loads_german(client):
    html = client.get("/", headers={"x-vercel-ip-country": "AT"}).get_data(as_text=True)
    assert 'lang="de"' in html
    assert "Lebensmittel" in html


# F7 — a US IP loads in English.
def test_us_ip_loads_english(client):
    html = client.get("/", headers={"x-vercel-ip-country": "US"}).get_data(as_text=True)
    assert 'lang="en"' in html
    assert "Compare" in html


# F3 — Austrian sees EU origins (Spain, Morocco, Netherlands), not Americas-only ones.
def test_eu_origins_for_austria(client):
    html = client.get("/", headers={"x-vercel-ip-country": "AT"}).get_data(as_text=True)
    assert "Spanien" in html and "Marokko" in html and "Niederlande" in html
    assert "Mexiko" not in html


# F3 — US sees Americas origins including US states.
def test_americas_origins_for_us(client):
    html = client.get("/", headers={"x-vercel-ip-country": "US"}).get_data(as_text=True)
    assert "Mexico" in html and "Peru" in html and "California" in html


# F7 — clicking the toggle persists the choice for the session.
def test_language_toggle_persists():
    with app.test_client() as c:
        c.get("/", headers={"x-vercel-ip-country": "AT"})  # would default to German
        c.get("/lang/en")                                   # override
        html = c.get("/", headers={"x-vercel-ip-country": "AT"}).get_data(as_text=True)
        assert 'lang="en"' in html


def test_health_endpoint(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["foods"] >= 40


# Live fragment render (the "local cheese vs imported strawberries" surprise).
def test_compare_live_renders_cards_fragment(client):
    r = client.get(
        "/compare/live",
        headers={"x-vercel-ip-country": "AT"},
        query_string={
            "food_a": "cheese", "qty_a": "200", "unit_a": "grams", "origin_a": "at",
            "food_b": "strawberry", "qty_b": "200", "unit_b": "grams", "origin_b": "es",
        },
    )
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    # It's a fragment, not a full page: no <html> wrapper, just the cards + delta.
    assert "<html" not in html
    assert 'class="cards"' in html and 'class="delta"' in html
    assert "Käse" in html and "Erdbeere" in html


# Live route tolerates missing params, falling back to beef vs tofu defaults.
def test_compare_live_defaults_to_beef_vs_tofu(client):
    html = client.get("/compare/live", headers={"x-vercel-ip-country": "US"}).get_data(as_text=True)
    assert "Beef" in html and "Tofu" in html


# The old POST /compare route is gone.
def test_old_compare_route_removed(client):
    assert client.post("/compare").status_code == 404
