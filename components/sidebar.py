"""Sidebar widget that owns all VRP parameters."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

# Must match the backend enums in app/schemas/vrp.py.
FIRST_SOLUTION_STRATEGIES = [
    "PATH_CHEAPEST_ARC",
    "SAVINGS",
    "CHRISTOFIDES",
    "PARALLEL_CHEAPEST_INSERTION",
    "AUTOMATIC",
]
LOCAL_SEARCH_METAHEURISTICS = [
    "GUIDED_LOCAL_SEARCH",
    "SIMULATED_ANNEALING",
    "TABU_SEARCH",
    "AUTOMATIC",
]
DEFAULT_FIRST_SOLUTION_STRATEGY = "PATH_CHEAPEST_ARC"
DEFAULT_LOCAL_SEARCH_METAHEURISTIC = "GUIDED_LOCAL_SEARCH"


@dataclass
class VRPParameters:
    depot_lat: float
    depot_lon: float
    n_vehicles: int
    capacity: int
    objective: str
    time_limit_seconds: int
    first_solution_strategy: str
    local_search_metaheuristic: str


def render_sidebar(default_lat: float = 40.4168, default_lon: float = -3.7038) -> VRPParameters:
    st.sidebar.header("Problem definition")

    with st.sidebar.expander("Depot location", expanded=True):
        col1, col2 = st.columns(2)
        depot_lat = col1.number_input("Latitude", value=default_lat, format="%.6f")
        depot_lon = col2.number_input("Longitude", value=default_lon, format="%.6f")

    with st.sidebar.expander("Fleet", expanded=True):
        n_vehicles = st.number_input("Number of vehicles", min_value=1, max_value=50, value=3)
        capacity = st.number_input("Capacity per vehicle", min_value=1, max_value=10_000, value=20)

    st.sidebar.header("Solver options")

    objective = st.sidebar.selectbox(
        "Objective",
        options=["duration", "distance"],
        index=0,
        help="Minimise total travel time or total travel distance.",
    )
    time_limit = st.sidebar.slider(
        "Time limit (seconds)", min_value=1, max_value=120, value=30,
        help="Wall-clock budget for the metaheuristic search.",
    )

    first_solution_strategy = st.sidebar.selectbox(
        "First-solution heuristic",
        options=FIRST_SOLUTION_STRATEGIES,
        index=FIRST_SOLUTION_STRATEGIES.index(DEFAULT_FIRST_SOLUTION_STRATEGY),
        help=(
            "How the initial feasible solution is built before local search: "
            "PATH_CHEAPEST_ARC (greedy cheapest arc), SAVINGS (Clarke & Wright), "
            "CHRISTOFIDES, PARALLEL_CHEAPEST_INSERTION, or AUTOMATIC."
        ),
    )
    local_search_metaheuristic = st.sidebar.selectbox(
        "Local-search metaheuristic",
        options=LOCAL_SEARCH_METAHEURISTICS,
        index=LOCAL_SEARCH_METAHEURISTICS.index(DEFAULT_LOCAL_SEARCH_METAHEURISTIC),
        help=(
            "How the initial solution is improved: GUIDED_LOCAL_SEARCH, "
            "SIMULATED_ANNEALING, TABU_SEARCH, or AUTOMATIC."
        ),
    )

    return VRPParameters(
        depot_lat=float(depot_lat),
        depot_lon=float(depot_lon),
        n_vehicles=int(n_vehicles),
        capacity=int(capacity),
        objective=objective,
        time_limit_seconds=int(time_limit),
        first_solution_strategy=first_solution_strategy,
        local_search_metaheuristic=local_search_metaheuristic,
    )
