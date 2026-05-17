"""Fetch customer locations from OpenStreetMap (OSMnx) for VRP demos."""

from __future__ import annotations

import random
from typing import List

import osmnx as ox
import pandas as pd


class OSMFetchError(Exception):
    """Raised when OSM returns nothing useful or the query fails."""


def parse_keyword_list(raw: str) -> List[str]:
    """Split comma-separated input; values are normalised to lowercase for OSM tags."""
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def fetch_customers_from_osm(
    place: str,
    *,
    tag_key: str = "amenity",
    keywords: str | List[str],
    limit: int,
    name_contains: str | None = None,
) -> pd.DataFrame:
    """Return a dataframe with columns id, name, latitude, longitude, demand.

    Each row's ``demand`` is drawn uniformly at random from 1..5.

    ``keywords`` are OSM tag *values* under ``tag_key`` (e.g. ``restaurant``).
    You may pass mixed case (e.g. ``Restaurant``); values are lowercased before querying.
    """

    place = place.strip()
    if not place:
        raise OSMFetchError("Place cannot be empty.")

    tag_key = tag_key.strip()
    if isinstance(keywords, str):
        values = parse_keyword_list(keywords)
    else:
        values = [str(v).strip().lower() for v in keywords if str(v).strip()]
    if not values:
        raise OSMFetchError("Provide at least one keyword (OSM tag value).")

    limit = max(1, min(int(limit), 1000))

    tags = {tag_key: values}
    try:
        gdf = ox.features_from_place(place, tags=tags)
    except Exception as exc:
        raise OSMFetchError(f"OSM / geocoder request failed: {exc}") from exc

    if gdf is None or gdf.empty:
        raise OSMFetchError(
            "No features found. Try another place, tag key, or keyword(s)."
        )

    keep = [c for c in ("name", tag_key, "geometry") if c in gdf.columns]
    if "geometry" not in keep:
        raise OSMFetchError("Query returned no geometry.")
    gdf = gdf[keep].copy()

    gdf["geometry"] = gdf.geometry.centroid
    gdf["longitude"] = gdf.geometry.x
    gdf["latitude"] = gdf.geometry.y

    out = gdf.drop(columns=["geometry"], errors="ignore")
    if tag_key in out.columns:
        out = out.rename(columns={tag_key: "category"})

    out = out.dropna(subset=["latitude", "longitude"])
    out = out[
        (out["longitude"].between(-180.0, 180.0)) & (out["latitude"].between(-90.0, 90.0))
    ]

    if name_contains and (needle := name_contains.strip()):
        names = out["name"].fillna("").astype(str)
        out = out[names.str.casefold().str.contains(needle.casefold(), regex=False)]

    out = out.drop_duplicates(subset=["latitude", "longitude"]).reset_index(drop=True)

    if len(out) > limit:
        out = out.iloc[:limit].reset_index(drop=True)

    if out.empty:
        raise OSMFetchError(
            "All rows were filtered out. Loosen the name filter or fetch more results."
        )

    out["name"] = out["name"].fillna("Unnamed").astype(str)
    out["id"] = [f"c{i + 1:02d}" for i in range(len(out))]
    out["demand"] = [random.randint(1, 5) for _ in range(len(out))]

    return out[["id", "name", "latitude", "longitude", "demand"]].copy()
