"""Turn a carbon number into a relatable "that's like ..." benchmark (PRD F5).

Each benchmark is an everyday activity with an approximate carbon cost. We pick
the one whose resulting count lands in the friendliest range (around 10), so a
small footprint and a large footprint naturally pick different benchmarks.
"""

import math

# Approximate kg CO2e per unit of each everyday activity. Order matters only as
# a tie-breaker. Sources are rough industry averages, cited loosely in the UI.
BENCHMARKS = [
    {"key": "bench_phone", "per_unit": 0.008},      # one smartphone charge
    {"key": "bench_bulb", "per_unit": 0.012},       # one hour of an LED bulb
    {"key": "bench_kettle", "per_unit": 0.06},      # one full kettle boil
    {"key": "bench_streaming", "per_unit": 0.055},  # one hour of video streaming
    {"key": "bench_driving", "per_unit": 0.17},     # one km in a petrol car
]

# Aim for counts near this magnitude so the phrase feels graspable.
TARGET_COUNT = 10


def _friendly_round(n):
    """Round a count to a readable value while keeping it >= 1."""
    if n >= 100:
        return int(round(n / 10.0) * 10)
    if n >= 10:
        return int(round(n))
    return round(n, 1)


def pick_benchmark(carbon_kg):
    """Return {"key": <translation key>, "n": <count>} or None if negligible.

    Chooses the benchmark whose count is closest (in log space) to TARGET_COUNT,
    considering only benchmarks that yield a count of at least 1. If the footprint
    is too small for any benchmark to reach 1, the most sensitive benchmark wins.
    """
    if carbon_kg <= 0:
        return None

    scored = []
    for b in BENCHMARKS:
        n = carbon_kg / b["per_unit"]
        scored.append((b["key"], n))

    eligible = [(key, n) for key, n in scored if n >= 1]
    if eligible:
        key, n = min(eligible, key=lambda kn: abs(math.log10(kn[1]) - math.log10(TARGET_COUNT)))
    else:
        # Footprint smaller than a single unit of everything: use the most
        # sensitive benchmark (largest count) so we still say something.
        key, n = max(scored, key=lambda kn: kn[1])

    return {"key": key, "n": _friendly_round(n)}
