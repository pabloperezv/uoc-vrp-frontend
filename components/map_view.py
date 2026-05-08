"""Folium-based interactive map renderer.

We chose Folium + ``streamlit-folium`` over PyDeck for light HTML maps and
simple popups. With ``osrm_base_url``, solution polylines follow the driving
network via OSRM ``/route``; otherwise straight segments between stops are used.
"""

from __future__ import annotations

from typing import Iterable

import folium
from folium.plugins import Fullscreen, MeasureControl

from services.osrm_route_geometry import fetch_driving_polyline

from utils.formatting import format_meters, format_seconds, vehicle_color


def _customer_display_name(
    customer_id: str | None, names_by_id: dict[str, str] | None
) -> tuple[str, str | None]:
    """Return (label for map, id for subtitle or None if depot)."""
    if customer_id is None:
        return "Depot", None
    cid = str(customer_id)
    if names_by_id and cid in names_by_id:
        return names_by_id[cid], cid
    return cid, cid


def _depot_marker(map_: folium.Map, lat: float, lon: float, name: str = "Depot") -> None:
    folium.Marker(
        location=[lat, lon],
        tooltip=name,
        popup=folium.Popup(f"<b>{name}</b><br/>Depot", max_width=200),
        icon=folium.Icon(color="black", icon="warehouse", prefix="fa"),
    ).add_to(map_)


def render_solution_map(
    depot: dict,
    routes: list[dict],
    *,
    height: int = 600,
    osrm_base_url: str | None = None,
    customer_names_by_id: dict[str, str] | None = None,
) -> folium.Map:
    """Build a Folium map with the depot, customer markers and route polylines.

    Parameters
    ----------
    depot : dict with keys ``coordinate.latitude`` / ``coordinate.longitude``
        and ``name`` for the depot marker.
    routes : list of ``VehicleRoute`` dicts as returned by the backend.
    osrm_base_url : OSRM HTTP origin (e.g. ``http://127.0.0.1:5000``). When set,
        polylines follow roads; on failure or when ``None``, straight lines are used.
    customer_names_by_id : ``customer_id`` -> display name for tooltips/popups. Use ``None`` to show ids only.
    """

    depot_lat = depot["coordinate"]["latitude"]
    depot_lon = depot["coordinate"]["longitude"]

    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, control_scale=True,
                   tiles="cartodbpositron")
    Fullscreen().add_to(m)
    MeasureControl(primary_length_unit="kilometers").add_to(m)

    _depot_marker(m, depot_lat, depot_lon, depot.get("name", "Depot"))

    for v_idx, route in enumerate(routes):
        color = vehicle_color(v_idx)
        layer = folium.FeatureGroup(
            name=f"Vehicle {route['vehicle_id']}", show=True
        )

        coords: list[tuple[float, float]] = []
        for stop in route["stops"]:
            lat = stop["coordinate"]["latitude"]
            lon = stop["coordinate"]["longitude"]
            coords.append((lat, lon))

            if stop["customer_id"] is None:
                continue

            title, cid_sub = _customer_display_name(
                stop["customer_id"], customer_names_by_id
            )
            id_line = f"ID: {cid_sub}<br/>" if cid_sub and cid_sub != title else ""
            popup_html = (
                f"<b>{title}</b><br/>"
                + id_line
                + f"Vehicle: {route['vehicle_id']}<br/>"
                f"Stop #: {stop['sequence']}<br/>"
                f"Load after: {stop['load']}<br/>"
                f"From depot: {format_meters(stop['arrival_distance_meters'])}, "
                f"{format_seconds(stop['arrival_duration_seconds'])}"
            )
            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=title,
            ).add_to(layer)

        if len(coords) >= 2:
            line_coords: list[tuple[float, float]] = list(coords)
            if osrm_base_url:
                road = fetch_driving_polyline(osrm_base_url, line_coords)
                if road:
                    line_coords = road
            folium.PolyLine(
                locations=line_coords,
                color=color,
                weight=4,
                opacity=0.85,
                tooltip=(
                    f"Vehicle {route['vehicle_id']} — "
                    f"{format_meters(route['total_distance_meters'])}, "
                    f"{format_seconds(route['total_duration_seconds'])}"
                ),
            ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    _fit_bounds(m, depot_lat, depot_lon, routes)
    m.options["height"] = height
    return m


def _fit_bounds(m: folium.Map, depot_lat: float, depot_lon: float,
                routes: Iterable[dict]) -> None:
    pts: list[tuple[float, float]] = [(depot_lat, depot_lon)]
    for r in routes:
        for s in r["stops"]:
            pts.append((s["coordinate"]["latitude"], s["coordinate"]["longitude"]))
    if len(pts) >= 2:
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20, 20))


def render_preview_map(
    depot_lat: float, depot_lon: float, customers_df, *, height: int = 450
) -> folium.Map:
    """Pre-solve preview: depot + customer markers, no routes."""

    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, control_scale=True,
                   tiles="cartodbpositron")
    _depot_marker(m, depot_lat, depot_lon)

    for _, row in customers_df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="#444",
            weight=1,
            fill=True,
            fill_color="#888",
            fill_opacity=0.85,
            popup=folium.Popup(
                f"<b>{row['name']}</b><br/>ID: {row['id']}<br/>demand {row['demand']}",
                max_width=220,
            ),
            tooltip=f"{row['name']}",
        ).add_to(m)

    m.options["height"] = height
    return m
