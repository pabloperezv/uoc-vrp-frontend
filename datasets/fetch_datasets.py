"""Fetch the validation datasets for the thesis experiments.

Uses the same OpenStreetMap query path as the application
(services.osm_customers.fetch_customers_from_osm), so the datasets are
real points of interest, identical in structure to what the app produces.

Generates 6 datasets: {Madrid, Barcelona, Sevilla} x {50, 300} restaurants.

Usage (from the repo root, with the project venv):
    .venv/bin/python docs/datasets/fetch_datasets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable so we can reuse the app's OSM logic.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.osm_customers import fetch_customers_from_osm  # noqa: E402

CITIES = ["Madrid", "Barcelona", "Sevilla"]
SIZES = [50, 300]
KEYWORD = "Restaurant"


def main() -> None:
    out_dir = Path(__file__).parent
    for city in CITIES:
        for size in SIZES:
            df = fetch_customers_from_osm(
                f"{city}, Spain",
                tag_key="amenity",
                keywords=KEYWORD,
                limit=size,
            )
            path = out_dir / f"{city.lower()}_{size}.csv"
            df.to_csv(path, index=False)
            print(f"{path.name}: {len(df)} customers")


if __name__ == "__main__":
    main()
