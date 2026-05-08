"""UOC VRP — Streamlit entrypoint.

Uses Streamlit's ``st.navigation`` API so that:
- the sidebar label of every page is fully controlled (no filename-magic),
- ``set_page_config`` is called **once** at the top level,
- pages can be either callables (defined here) or paths to script files.
"""

from __future__ import annotations

import streamlit as st

from utils.branding import FAVICON_PATH, UOC_LOGO_PATH, UOC_WEB_URL
from utils.settings import get_settings
from utils.support import render_bug_report_corner

_page_icon = (
    str(FAVICON_PATH)
    if FAVICON_PATH.is_file()
    else (str(UOC_LOGO_PATH) if UOC_LOGO_PATH.is_file() else None)
)
st.set_page_config(
    page_title="UOC VRP Solver",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

if UOC_LOGO_PATH.is_file():
    st.logo(str(UOC_LOGO_PATH), size="large", link=UOC_WEB_URL)

render_bug_report_corner()


def get_started_page() -> None:
    st.markdown("## Get Started")
    st.markdown(
        "Plan optimal multi-vehicle delivery routes powered by **Google OR-Tools** "
        "and real-world travel times from **OSRM**.\n\n"
        "Use the **Solver** page on the left to upload your customers and run an optimisation."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        _backend_status()
    with col2:
        _instructions()


def _backend_status() -> None:
    settings = get_settings()
    with st.container(border=True):
        st.markdown("#### Backend status")
        st.caption(f"`{settings.backend_url}`")

        try:
            import requests
            r = requests.get(settings.health_endpoint, timeout=3)
            r.raise_for_status()
            data = r.json()
            st.success(
                f"Connected to **{data.get('app', 'backend')}** "
                f"v{data.get('version', '?')} ({data.get('environment', '?')})."
            )
        except Exception as exc:
            st.error(f"Backend unreachable: {exc}")
            st.caption("Edit `BACKEND_URL` in `.streamlit/secrets.toml` to point to your API.")


def _instructions() -> None:
    with st.container(border=True):
        st.markdown(
            "#### How it works\n"
            "1. **Upload** a CSV with your customers (`id`, `name`, `latitude`, `longitude`, `demand`).\n"
            "2. **Configure** the depot location, fleet size, capacity and solver options in the sidebar.\n"
            "3. **Solve**: the backend builds an OSRM travel matrix and runs OR-Tools.\n"
            "4. **Inspect** the optimised routes on the interactive map and metric cards.\n"
        )


# --------------------------------------------------------------- Navigation --


pages = [
    st.Page(get_started_page, title="Get Started", icon=None, default=True),
    st.Page("pages/1_Solver.py", title="Solver", icon=None),
    st.Page("pages/2_About.py", title="About", icon=None),
]

st.navigation(pages).run()
