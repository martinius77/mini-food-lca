"""Transport distance + mode selection + emissions.

We don't call a live distance API. Instead we keep lat/lon for each origin and
each user country in ``origins.csv`` and compute great-circle (haversine)
distance. Mode is chosen from distance bands, with air freight reserved for
perishable goods travelling a long way.
"""

import math

from .data_loader import load_origins, load_transport_factors

# Distance band thresholds in km (see PRD F4).
SHORT_KM = 300
MEDIUM_KM = 2000

# Sentinel origin meaning "user doesn't know" -> world average, no transport leg.
AVERAGE_ORIGIN = "average"


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometres."""
    radius = 6371.0  # Earth radius in km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _user_origin_id(user_country):
    """Map a 2-letter country code (e.g. 'AT') to an origins.csv id (e.g. 'at')."""
    if not user_country:
        return None
    return user_country.lower()


def distance_for(origin_id, user_country):
    """Distance in km from origin to the user's country. None if not resolvable."""
    origins = load_origins()
    dest_id = _user_origin_id(user_country)
    if origin_id not in origins or dest_id not in origins:
        return None
    o = origins[origin_id]
    d = origins[dest_id]
    return haversine_km(o["lat"], o["lon"], d["lat"], d["lon"])


def select_mode(distance_km, perishable):
    """Pick a transport mode from the distance band (PRD F4)."""
    if distance_km <= SHORT_KM:
        return "truck"
    if distance_km <= MEDIUM_KM:
        return "rail"
    # Long haul: sea freight by default, air for perishable goods.
    return "air" if perishable else "sea"


def transport_footprint(origin_id, user_country, mass_kg, perishable):
    """Return the transport leg as a dict.

    Keys: distance_km, mode, carbon (kg CO2e). For the "average / don't know"
    origin (or any origin we can't place) we honestly add no transport leg and
    report mode ``None`` so the UI can say production-only.
    """
    if origin_id == AVERAGE_ORIGIN:
        return {"distance_km": None, "mode": None, "carbon": 0.0}

    distance_km = distance_for(origin_id, user_country)
    if distance_km is None:
        return {"distance_km": None, "mode": None, "carbon": 0.0}

    mode = select_mode(distance_km, perishable)
    factor = load_transport_factors()[mode]["factor"]  # kg CO2e per tonne-km
    carbon = factor * (mass_kg / 1000.0) * distance_km
    return {"distance_km": distance_km, "mode": mode, "carbon": carbon}
