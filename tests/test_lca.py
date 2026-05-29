"""Acceptance tests mapped to the PRD feature tests (F1-F7)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.comparisons import pick_benchmark
from src.data_loader import load_foods
from src.lca import calculate_footprint, compare


# F1 — identical items in identical quantities return identical results.
def test_identical_selections_are_equal():
    sel = {"food_id": "chicken", "quantity": 100, "origin": "es", "user_country": "AT", "unit": "grams"}
    a = calculate_footprint(**sel)
    b = calculate_footprint(**sel)
    assert a == b
    assert compare(sel, sel)["delta_pct"] == 0.0


# F1 — changing food B updates only B's numbers and the delta.
def test_changing_b_leaves_a_unchanged():
    sel_a = {"food_id": "chicken", "quantity": 100, "origin": "es", "user_country": "AT", "unit": "grams"}
    sel_b1 = {"food_id": "tofu", "quantity": 100, "origin": "es", "user_country": "AT", "unit": "grams"}
    sel_b2 = {"food_id": "beef", "quantity": 100, "origin": "es", "user_country": "AT", "unit": "grams"}

    r1 = compare(sel_a, sel_b1)
    r2 = compare(sel_a, sel_b2)

    assert r1["a"] == r2["a"]              # A untouched
    assert r1["b"] != r2["b"]              # B changed
    assert r1["delta_pct"] != r2["delta_pct"]


# F2 — every food has carbon + water + land-use factors loaded.
def test_every_food_has_all_factors():
    foods = load_foods()
    assert len(foods) >= 40
    for f in foods.values():
        for key in ("carbon", "water", "land", "grams_per_item"):
            assert f[key] > 0


# F4 — banana from Ecuador to Austria > banana from Spain to Austria.
def test_transport_distance_increases_footprint():
    far = calculate_footprint("banana", 1, "ec", "AT", unit="item")
    near = calculate_footprint("banana", 1, "es", "AT", unit="item")
    assert far["carbon"]["value"] > near["carbon"]["value"]


# F4 — perishable goods shipped far are flagged as air-freighted.
def test_perishable_long_haul_flagged_air():
    res = calculate_footprint("strawberry", 100, "pe", "AT", unit="grams")
    assert res["air_flagged"] is True


# F5 — a small result and a large result pick different benchmarks.
def test_benchmark_scales_with_magnitude():
    small = pick_benchmark(0.1)
    large = pick_benchmark(10)
    assert small is not None and large is not None
    assert small["key"] != large["key"]


# F6 — every displayed value has a +/- component.
def test_every_value_has_uncertainty_band():
    res = calculate_footprint("cheese", 200, "at", "AT", unit="grams")
    for impact in ("carbon", "water", "land"):
        band = res[impact]
        assert band["lower"] < band["value"] < band["upper"]


# "Average / don't know" origin adds no transport leg.
def test_average_origin_has_no_transport():
    res = calculate_footprint("apple", 1, "average", "AT", unit="item")
    assert res["transport_mode"] is None
    assert res["carbon_breakdown"]["transport"] == 0.0
