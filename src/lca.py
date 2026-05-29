"""Core footprint calculation: production + transport, with uncertainty.

System boundary is cradle-to-gate (production) plus a transport leg from the
origin to the user's country. Water and land use are production-only; transport
adds to carbon only. Every returned number carries a +/-30% uncertainty band.
"""

from .comparisons import pick_benchmark
from .data_loader import load_foods
from .transport import transport_footprint

# Typical uncertainty on the underlying source data (PRD F6).
UNCERTAINTY = 0.30


def _band(value):
    """Wrap a point estimate in a +/-UNCERTAINTY range."""
    return {
        "value": value,
        "lower": value * (1 - UNCERTAINTY),
        "upper": value * (1 + UNCERTAINTY),
    }


def mass_kg(food, quantity, unit):
    """Convert a quantity + unit into kilograms for the given food."""
    if unit == "grams":
        return quantity / 1000.0
    # unit == "item": use the food's typical item weight.
    return quantity * food["grams_per_item"] / 1000.0


def calculate_footprint(food_id, quantity, origin, user_country, unit="item"):
    """Compute carbon, water and land use for one food selection.

    Returns a dict with each impact as a {value, lower, upper} band, a carbon
    breakdown (production vs transport) for the hotspot bar, the transport mode
    and distance, an air-freight flag, and a relatable benchmark for carbon.
    """
    foods = load_foods()
    food = foods[food_id]

    kg = mass_kg(food, quantity, unit)

    production_carbon = food["carbon"] * kg
    water = food["water"] * kg
    land = food["land"] * kg

    transport = transport_footprint(origin, user_country, kg, food["perishable"])
    transport_carbon = transport["carbon"]
    carbon_total = production_carbon + transport_carbon

    # Hotspot breakdown for the bar under the carbon total.
    if carbon_total > 0:
        production_pct = production_carbon / carbon_total * 100
        transport_pct = transport_carbon / carbon_total * 100
    else:
        production_pct = transport_pct = 0.0

    return {
        "food_id": food_id,
        "mass_kg": kg,
        "carbon": _band(carbon_total),
        "water": _band(water),
        "land": _band(land),
        "carbon_breakdown": {
            "production": production_carbon,
            "transport": transport_carbon,
            "production_pct": production_pct,
            "transport_pct": transport_pct,
        },
        "transport_mode": transport["mode"],
        "transport_distance_km": transport["distance_km"],
        "air_flagged": transport["mode"] == "air",
        "benchmark": pick_benchmark(carbon_total),
    }


def compare(selection_a, selection_b):
    """Run two selections and attach the carbon delta of B relative to A.

    Each selection is a dict of kwargs for calculate_footprint. The delta is the
    signed percentage difference of B's carbon vs A's carbon.
    """
    a = calculate_footprint(**selection_a)
    b = calculate_footprint(**selection_b)

    a_carbon = a["carbon"]["value"]
    if a_carbon > 0:
        pct = (b["carbon"]["value"] - a_carbon) / a_carbon * 100
    else:
        pct = 0.0

    return {"a": a, "b": b, "delta_pct": pct}
