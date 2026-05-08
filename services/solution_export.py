"""Export VRP solution: Folium map HTML and multi-sheet Excel (one tab per vehicle)."""

from __future__ import annotations

import io
import re

import folium
import pandas as pd


def folium_map_to_html_bytes(m: folium.Map) -> bytes:
    """Serialize a Folium map to UTF-8 HTML for download."""
    buf = io.BytesIO()
    m.save(buf, close_file=False)
    buf.seek(0)
    return buf.getvalue()


def _safe_excel_sheet_name(name: str) -> str:
    """Excel sheet names: max 31 chars; cannot contain []:*?/\\."""
    s = re.sub(r"[\[\]\:\*\?\/\\]", "_", str(name).strip())
    return s[:31] if s else "vehicle"


def routes_to_excel_bytes(routes: list[dict]) -> bytes:
    """Build an .xlsx with one worksheet per vehicle (summary + stop details)."""
    buf = io.BytesIO()
    used: set[str] = set()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for r in routes:
            base = _safe_excel_sheet_name(r["vehicle_id"])
            sheet = base
            n = 1
            while sheet in used:
                suffix = f"_{n}"
                sheet = (base[: 31 - len(suffix)] + suffix)[:31]
                n += 1
            used.add(sheet)

            summary = pd.DataFrame(
                [
                    ("vehicle_id", r["vehicle_id"]),
                    ("total_distance_meters", r["total_distance_meters"]),
                    ("total_duration_seconds", r["total_duration_seconds"]),
                    ("total_load", r["total_load"]),
                ],
                columns=["field", "value"],
            )
            stops = pd.DataFrame(
                [
                    {
                        "sequence": s["sequence"],
                        "customer_id": s["customer_id"] or "DEPOT",
                        "latitude": s["coordinate"]["latitude"],
                        "longitude": s["coordinate"]["longitude"],
                        "load_after_stop": s["load"],
                        "arrival_distance_meters": s["arrival_distance_meters"],
                        "arrival_duration_seconds": s["arrival_duration_seconds"],
                    }
                    for s in r["stops"]
                ]
            )

            summary.to_excel(writer, sheet_name=sheet, index=False, startrow=0)
            stops.to_excel(writer, sheet_name=sheet, index=False, startrow=len(summary) + 2)

    buf.seek(0)
    return buf.getvalue()
