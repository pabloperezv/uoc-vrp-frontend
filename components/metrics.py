"""KPI cards and per-route table."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.formatting import format_meters, format_seconds, vehicle_color


def render_metrics(metrics: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total distance", format_meters(metrics["total_distance_meters"]))
    col2.metric("Total duration", format_seconds(metrics["total_duration_seconds"]))
    col3.metric("Vehicles used", metrics["vehicles_used"])
    col4.metric("Customers served", metrics["customers_served"])

    st.caption(
        f"Solver status: `{metrics['solver_status']}` — "
        f"wall time {metrics['solve_wall_time_seconds']:.2f}s"
    )


def render_routes_table(routes: list[dict]) -> None:
    rows = []
    for idx, r in enumerate(routes):
        rows.append({
            "Vehicle": r["vehicle_id"],
            "Stops": sum(1 for s in r["stops"] if s["customer_id"] is not None),
            "Load": r["total_load"],
            "Distance": format_meters(r["total_distance_meters"]),
            "Duration": format_seconds(r["total_duration_seconds"]),
            "Color": vehicle_color(idx),
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Color": st.column_config.TextColumn("Color", help="Map color"),
        },
    )


def render_route_details(
    routes: list[dict], *, customer_names_by_id: dict[str, str] | None = None
) -> None:
    for idx, r in enumerate(routes):
        title = (
            f"Vehicle {r['vehicle_id']} — "
            f"{format_meters(r['total_distance_meters'])}, "
            f"{format_seconds(r['total_duration_seconds'])} — "
            f"load {r['total_load']}"
        )
        with st.expander(title, expanded=False):
            rows = []
            for s in r["stops"]:
                cid = s["customer_id"]
                if cid is None:
                    cust = "DEPOT"
                else:
                    key = str(cid)
                    cust = customer_names_by_id.get(key, key) if customer_names_by_id else key
                rows.append({
                    "Seq": s["sequence"],
                    "Customer": cust,
                    "Lat": s["coordinate"]["latitude"],
                    "Lon": s["coordinate"]["longitude"],
                    "Load": s["load"],
                    "From depot (m)": round(s["arrival_distance_meters"]),
                    "From depot": format_seconds(s["arrival_duration_seconds"]),
                })
            stops_df = pd.DataFrame(rows)
            st.dataframe(stops_df, hide_index=True, use_container_width=True)
