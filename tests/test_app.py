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


# Live route returns JSON of formatted display strings (the cheese vs strawberry
# surprise), with German decimal formatting preserved by the server.
def test_compare_live_returns_json(client):
    r = client.get(
        "/compare/live",
        headers={"x-vercel-ip-country": "AT"},
        query_string={
            "food_a": "cheese", "qty_a": "200", "unit_a": "grams", "origin_a": "at",
            "food_b": "strawberry", "qty_b": "200", "unit_b": "grams", "origin_b": "es",
        },
    )
    assert r.status_code == 200
    assert r.mimetype == "application/json"
    data = r.get_json()
    assert set(data.keys()) == {"a", "b", "verdict"}
    assert data["a"]["name"] == "Käse" and data["b"]["name"] == "Erdbeere"
    # Each food carries formatted strings, no raw numbers, no calculation client-side.
    for key in ("carbon", "carbon-range", "water", "land", "benchmark"):
        assert key in data["a"]
    # German decimals use a comma (e.g. "4,8"), proving Python did the formatting.
    assert "," in data["a"]["carbon"]
    assert "Erdbeere" in data["verdict"] and "Käse" in data["verdict"]


# Live route tolerates missing params, falling back to beef vs tofu defaults.
def test_compare_live_defaults_to_beef_vs_tofu(client):
    data = client.get("/compare/live", headers={"x-vercel-ip-country": "US"}).get_json()
    assert data["a"]["name"] == "Beef" and data["b"]["name"] == "Tofu"


# Index page exposes the empty target elements JS fills, and the verdict banner.
def test_index_has_live_targets(client):
    html = client.get("/", headers={"x-vercel-ip-country": "US"}).get_data(as_text=True)
    for el_id in ("carbon-a", "carbon-range-a", "water-a", "land-a", "benchmark-a",
                  "carbon-b", "water-b", "land-b", "benchmark-b"):
        assert 'id="' + el_id + '"' in html
    assert 'id="verdict"' in html


# The old POST /compare route is gone.
def test_old_compare_route_removed(client):
    assert client.post("/compare").status_code == 404
