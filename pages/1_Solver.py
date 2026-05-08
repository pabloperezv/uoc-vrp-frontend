"""Solver page: upload, configure, solve, visualise."""

from __future__ import annotations

from typing import Any

import streamlit as st
from streamlit_folium import st_folium

from components.map_view import render_preview_map, render_solution_map
from components.metrics import render_metrics, render_route_details, render_routes_table
from components.sidebar import render_sidebar
from services.api_client import BackendError, VRPApiClient
from services.csv_loader import CSVValidationError, build_solve_payload, load_customers
from services.osm_customers import OSMFetchError, fetch_customers_from_osm
from services.solution_export import folium_map_to_html_bytes, routes_to_excel_bytes
from utils.settings import get_settings

st.title("VRP Solver")

settings = get_settings()
client = VRPApiClient(settings)

_PENDING_FEASIBILITY = "_uoc_vrp_pending_feasibility"


def _fleet_capacity(n_vehicles: int, capacity: int) -> int:
    return int(n_vehicles) * int(capacity)


def _total_demand(customers_df: Any) -> int:
    s = customers_df["demand"].sum()
    return int(s)


@st.dialog("Capacity check")
def _feasibility_dialog() -> None:
    info = st.session_state.get(_PENDING_FEASIBILITY)
    if not info:
        return
    st.warning(
        f"Total demand (**{info['total_demand']}**) is greater than fleet capacity "
        f"({info['n_vehicles']} × {info['capacity']} = **{info['fleet_cap']}**). "
        "Increase capacity or add vehicles in the sidebar, then try again."
    )
    if st.button("OK", type="primary", use_container_width=True):
        del st.session_state[_PENDING_FEASIBILITY]
        st.rerun()


def _run_solve(payload: dict[str, Any]) -> None:
    progress = st.empty()
    try:

        def _on_ev(ev: dict) -> None:
            t = ev.get("type")
            if t == "stage":
                progress.caption(f"Stage: **{ev.get('stage', '')}**")
            elif t == "poll":
                progress.caption(
                    f"Polling… status **{ev.get('status', '')}** "
                    f"(stage {ev.get('stage', '')})"
                )
            elif t == "ws_fallback":
                progress.caption(f"WebSocket unavailable, using HTTP polling ({ev.get('detail', '')[:80]})")
            elif t == "sync_fallback":
                progress.caption(ev.get("detail", "Using synchronous solve…"))

        with st.spinner("Optimising routes…"):
            result = client.solve_via_async_job(payload, on_event=_on_ev)
        progress.empty()
        st.session_state["last_result"] = result
        st.session_state["last_payload"] = payload
    except BackendError as exc:
        progress.empty()
        st.error(f"Solver error: {exc}")
        if exc.payload:
            with st.expander("Backend response"):
                st.json(exc.payload)
        st.stop()


# ---------------------------------------------------------------------------- 1. Upload

st.subheader("1. Customers")

uploaded = st.file_uploader(
    "Upload a CSV with columns: id, name, latitude, longitude, demand",
    type=["csv"],
)

st.markdown(
    "<p style='text-align: center; color: #6b7280; font-size: 0.9rem; "
    "margin: 0.35rem 0 0.5rem 0;'>Or</p>",
    unsafe_allow_html=True,
)

with st.expander("Fetch sample from OpenStreetMap", expanded=False):
    oc1, oc2 = st.columns(2)
    with oc1:
        osm_place = st.text_input("Place", value="Barcelona, Spain", key="osm_place")
        osm_kw = st.text_input(
            "Keyword",
            value="Restaurant",
            help="Comma-separated **amenity** values, e.g. `Restaurant, cafe`.",
            key="osm_keywords",
        )
    with oc2:
        osm_n = st.number_input(
            "Number of stores (max)",
            min_value=5,
            max_value=400,
            value=25,
            step=5,
            key="osm_limit",
        )
    if st.button("Fetch & load customers", key="osm_fetch_btn", use_container_width=True):
        try:
            with st.spinner("Querying OpenStreetMap…"):
                df_osm = fetch_customers_from_osm(
                    osm_place,
                    tag_key="amenity",
                    keywords=osm_kw,
                    limit=int(osm_n),
                )
            st.session_state["customers_df"] = df_osm
            st.success(f"Loaded **{len(df_osm)}** locations from OSM.")
        except OSMFetchError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

if uploaded is not None:
    try:
        st.session_state["customers_df"] = load_customers(uploaded)
        st.success(f"Loaded {len(st.session_state['customers_df'])} customers.")
    except CSVValidationError as exc:
        st.error(str(exc))

customers_df = st.session_state.get("customers_df")
if customers_df is not None:
    with st.expander(f"Preview — {len(customers_df)} rows", expanded=False):
        st.dataframe(customers_df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------- 2. Sidebar parameters

default_lat = float(customers_df["latitude"].mean()) if customers_df is not None else 40.4168
default_lon = float(customers_df["longitude"].mean()) if customers_df is not None else -3.7038
params = render_sidebar(default_lat=default_lat, default_lon=default_lon)


# ---------------------------------------------------------------------------- 3. Pre-solve preview

if customers_df is not None:
    st.subheader("2. Preview")
    preview_map = render_preview_map(params.depot_lat, params.depot_lon, customers_df)
    st_folium(preview_map, width=None, height=420, returned_objects=[])


# ---------------------------------------------------------------------------- 4. Solve

st.subheader("3. Solve")

if _PENDING_FEASIBILITY in st.session_state:
    _feasibility_dialog()

solve_disabled = customers_df is None
solve_clicked = st.button(
    "Solve VRP",
    type="primary",
    disabled=solve_disabled,
    use_container_width=False,
)

if solve_clicked and customers_df is not None:
    payload = build_solve_payload(
        customers=customers_df,
        depot_lat=params.depot_lat,
        depot_lon=params.depot_lon,
        n_vehicles=params.n_vehicles,
        capacity=params.capacity,
        objective=params.objective,
        time_limit_seconds=params.time_limit_seconds,
        first_solution_strategy=params.first_solution_strategy,
        local_search_metaheuristic=params.local_search_metaheuristic,
    )
    td = _total_demand(customers_df)
    fc = _fleet_capacity(params.n_vehicles, params.capacity)
    if td > fc:
        st.session_state[_PENDING_FEASIBILITY] = {
            "payload": payload,
            "total_demand": td,
            "fleet_cap": fc,
            "n_vehicles": params.n_vehicles,
            "capacity": params.capacity,
        }
        st.rerun()
    _run_solve(payload)


# ---------------------------------------------------------------------------- 5. Results

result = st.session_state.get("last_result")
if result is not None and customers_df is not None:
    st.subheader("4. Results")

    render_metrics(result["metrics"])

    depot = st.session_state["last_payload"]["depot"]
    customer_names_by_id = {
        str(row["id"]): str(row["name"]) for _, row in customers_df.iterrows()
    }
    solution_map = render_solution_map(
        depot,
        result["routes"],
        osrm_base_url=settings.osrm_base_url,
        customer_names_by_id=customer_names_by_id,
    )
    map_html = folium_map_to_html_bytes(solution_map)
    xlsx_bytes = routes_to_excel_bytes(result["routes"])

    tab_map, tab_routes, tab_details = st.tabs(["Map", "Routes", "Details"])

    with tab_map:
        st_folium(solution_map, width=None, height=620, returned_objects=[])

    with tab_routes:
        render_routes_table(result["routes"])

    with tab_details:
        render_route_details(result["routes"], customer_names_by_id=customer_names_by_id)

    st.markdown(
        """
        <style>
        [data-testid="stDownloadButton"] button {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
        }
        [data-testid="stDownloadButton"] button:hover {
            background-color: #1d4ed8 !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        [data-testid="stDownloadButton"] button:focus-visible {
            box-shadow: #2563eb 0px 0px 0px 0.2rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("##### Export")
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            label="Download map (HTML)",
            data=map_html,
            file_name="vrp_solution_map.html",
            mime="text/html",
            use_container_width=True,
            help="Interactive map: open in a browser (same view as above, with layers).",
        )
    with dl2:
        st.download_button(
            label="Download routes (Excel)",
            data=xlsx_bytes,
            file_name="vrp_routes_by_vehicle.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="One worksheet per vehicle: summary metrics and stop-by-stop details.",
        )
