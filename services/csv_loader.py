"""CSV ingestion helpers.

Expected schema (case-insensitive column names, in any order):

    id,name,latitude,longitude,demand

- ``id``        : unique customer identifier (string).
- ``name``      : non-empty human-friendly label (shown on maps).
- ``latitude``  : WGS84.
- ``longitude`` : WGS84.
- ``demand``    : non-negative whole number.
"""

from __future__ import annotations

from io import BytesIO
from typing import IO

import pandas as pd

REQUIRED_COLUMNS = {"id", "name", "latitude", "longitude", "demand"}


class CSVValidationError(ValueError):
    pass


def load_customers(file: IO[bytes] | BytesIO) -> pd.DataFrame:
    try:
        df = pd.read_csv(file)
    except Exception as exc:
        raise CSVValidationError(f"Could not parse CSV: {exc}") from exc

    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise CSVValidationError(
            f"CSV is missing columns: {sorted(missing)}. "
            f"Expected: {sorted(REQUIRED_COLUMNS)}."
        )

    df["id"] = df["id"].astype(str)
    if df["id"].duplicated().any():
        dups = df.loc[df["id"].duplicated(), "id"].tolist()
        raise CSVValidationError(f"Duplicate customer ids: {dups[:5]}")

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    if df[["latitude", "longitude"]].isna().any().any():
        raise CSVValidationError("Some rows have non-numeric latitude/longitude.")

    if not df["latitude"].between(-90, 90).all():
        raise CSVValidationError("Latitude must be in [-90, 90].")
    if not df["longitude"].between(-180, 180).all():
        raise CSVValidationError("Longitude must be in [-180, 180].")

    df["demand"] = pd.to_numeric(df["demand"], errors="coerce")
    if df["demand"].isna().any():
        bad = df.index[df["demand"].isna()].tolist()[:10]
        raise CSVValidationError(
            f"Demand must be a number for every row (check 0-based row indices: {bad})."
        )
    demand_rounded = df["demand"].round()
    if (df["demand"] - demand_rounded).abs().max() > 1e-9:
        raise CSVValidationError("Demand values must be whole numbers.")
    df["demand"] = demand_rounded.astype(int)
    if (df["demand"] < 0).any():
        raise CSVValidationError("Demand must be non-negative.")

    df["name"] = df["name"].fillna("").astype(str).str.strip()
    if (df["name"] == "").any():
        bad = df.index[df["name"] == ""].tolist()[:10]
        raise CSVValidationError(
            f"Every customer needs a non-empty name (check rows / 0-based indices: {bad})."
        )

    return df[["id", "name", "latitude", "longitude", "demand"]].reset_index(drop=True)


def build_solve_payload(
    customers: pd.DataFrame,
    depot_lat: float,
    depot_lon: float,
    n_vehicles: int,
    capacity: int,
    objective: str,
    time_limit_seconds: int,
    first_solution_strategy: str,
    local_search_metaheuristic: str,
) -> dict:
    """Translate UI state into the backend ``SolveRequest`` JSON payload."""

    return {
        "depot": {
            "id": "depot",
            "name": "Depot",
            "coordinate": {"latitude": float(depot_lat), "longitude": float(depot_lon)},
        },
        "customers": [
            {
                "id": str(row["id"]),
                "name": str(row["name"]),
                "coordinate": {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                },
                "demand": int(row["demand"]),
            }
            for _, row in customers.iterrows()
        ],
        "vehicles": [
            {"id": f"v{i + 1}", "capacity": int(capacity)}
            for i in range(int(n_vehicles))
        ],
        "options": {
            "objective": objective,
            "time_limit_seconds": int(time_limit_seconds),
            "first_solution_strategy": first_solution_strategy,
            "local_search_metaheuristic": local_search_metaheuristic,
        },
    }
