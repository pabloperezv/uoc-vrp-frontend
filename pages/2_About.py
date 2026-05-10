"""About page — context for thesis defenders / examiners."""

from __future__ import annotations

import streamlit as st

st.title("About this project")

st.markdown(
    """
This application is part of a **Master's Thesis at UOC** focused on solving the
Vehicle Routing Problem (VRP) developed by **Pablo Perez Verdugo**.

### Architecture

- **Frontend** — Streamlit (this app), deployed on Streamlit Community Cloud.
- **Backend** — FastAPI service deployed on a private Ubuntu server, packaged
  with Docker Compose.
- **Routing engine** — OSRM container serving precomputed road-network data.
- **Optimisation** — Google OR-Tools metaheuristic VRP solver.

### Why this stack?

| Choice | Rationale |
|--------|-----------|
| Streamlit | Pythonic UI, zero-config deployment, perfect for academic work. |
| FastAPI   | Async, OpenAPI out of the box, Pydantic validation. |
| OR-Tools  | State-of-the-art metaheuristics, free, well-maintained. |
| OSRM      | Open-source, fast, deterministic shortest paths on real road data. |
| Docker Compose | Reproducible deployment for both API and OSRM. |

### Repositories

- https://github.com/pabloperezv/uoc-vrp-frontend
- https://github.com/pabloperezv/uoc-vrp-backend
"""
)
