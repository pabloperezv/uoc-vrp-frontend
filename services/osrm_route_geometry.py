"""Fetch road-following polylines from a local or remote OSRM instance (GET /route)."""

from __future__ import annotations

from typing import List, Tuple

import requests

# Match backend `app/services/osrm/client.py` defaults.
DEFAULT_PROFILE = "driving"


def fetch_driving_polyline(
    base_url: str,
    lat_lon_points: List[Tuple[float, float]],
    *,
    profile: str = DEFAULT_PROFILE,
    timeout_seconds: float = 25.0,
) -> List[Tuple[float, float]] | None:
    """Return ``[(lat, lon), ...]`` along the driving network, or ``None`` on failure.

    ``lat_lon_points`` follows Folium order (latitude first). OSRM URLs use ``lon,lat``.
    A single request is issued with all waypoints in visit order (one polyline per vehicle).
    """

    if len(lat_lon_points) < 2:
        return list(lat_lon_points)

    base = base_url.rstrip("/")
    coord_str = ";".join(
        f"{float(lon):.6f},{float(lat):.6f}" for lat, lon in lat_lon_points
    )
    url = f"{base}/route/v1/{profile}/{coord_str}"
    try:
        r = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=timeout_seconds,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None

    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    try:
        geometry = data["routes"][0]["geometry"]["coordinates"]
    except (KeyError, IndexError, TypeError):
        return None

    # GeoJSON positions are [lon, lat]; Folium expects [lat, lon].
    out: List[Tuple[float, float]] = []
    for pt in geometry:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        lon, lat = float(pt[0]), float(pt[1])
        out.append((lat, lon))
    return out if len(out) >= 2 else None
