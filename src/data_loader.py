"""Load the static data files (CSV + JSON) once and cache them in memory.

All the project's reference data lives in the top-level ``data/`` directory.
These tables are small and never change at runtime, so we read them once on
first access and hand back cached structures afterwards.
"""

import csv
import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _read_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def load_foods():
    """Return {food_id: {...}} with numeric fields coerced to float/int/bool."""
    foods = {}
    for row in _read_csv("food_factors.csv"):
        foods[row["id"]] = {
            "id": row["id"],
            "name_en": row["name_en"],
            "name_de": row["name_de"],
            "category": row["category"],
            "carbon": float(row["carbon_kg_co2e_per_kg"]),
            "water": float(row["water_l_per_kg"]),
            "land": float(row["land_m2_per_kg"]),
            "perishable": row["perishable"] == "1",
            "grams_per_item": float(row["grams_per_item"]),
        }
    return foods


@lru_cache(maxsize=1)
def load_origins():
    """Return {origin_id: {...}} with regions as a list and lat/lon as floats."""
    origins = {}
    for row in _read_csv("origins.csv"):
        origins[row["id"]] = {
            "id": row["id"],
            "name_en": row["name_en"],
            "name_de": row["name_de"],
            "regions": row["regions"].split(";"),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
        }
    return origins


@lru_cache(maxsize=1)
def load_transport_factors():
    """Return {mode: {...}} keyed by transport mode."""
    modes = {}
    for row in _read_csv("transport_factors.csv"):
        modes[row["mode"]] = {
            "mode": row["mode"],
            "name_en": row["name_en"],
            "name_de": row["name_de"],
            "factor": float(row["kg_co2e_per_tonne_km"]),
        }
    return modes


@lru_cache(maxsize=1)
def load_translations():
    path = os.path.join(DATA_DIR, "translations.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
