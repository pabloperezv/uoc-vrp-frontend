"""Support / feedback helpers."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

import streamlit as st

BUG_REPORT_EMAIL = "pablo.perez.tech@gmail.com"

# Fixed viewport corner for the mailto link (does not scroll with the sidebar).
# Switch to "top-right" if you prefer it above the main content.
BugReportCorner = Literal["bottom-right", "top-right"]
BUG_REPORT_FLOAT_CORNER: BugReportCorner = "bottom-right"


def bug_report_mailto_url() -> str:
    subject = quote("UOC VRP Bug report", safe="")
    return f"mailto:{BUG_REPORT_EMAIL}?subject={subject}"


def bug_report_corner_html(*, corner: BugReportCorner | None = None) -> str:
    """HTML + CSS: fixed mailto link in a main-window corner (not the sidebar)."""
    where = corner or BUG_REPORT_FLOAT_CORNER
    pos = (
        "top: 4.75rem; bottom: auto;"
        if where == "top-right"
        else "bottom: 1rem; top: auto;"
    )
    url = bug_report_mailto_url()
    return f"""<style>
a.st-bug-report-corner {{
  position: fixed;
  {pos}
  right: 1rem;
  z-index: 999991;
  font-size: 14px;
  line-height: 1.2;
  color: rgba(49, 51, 63, 0.55);
  text-decoration: none !important;
}}
a.st-bug-report-corner:hover {{
  color: rgba(49, 51, 63, 0.95);
  text-decoration: underline !important;
}}
@media (prefers-color-scheme: dark) {{
  a.st-bug-report-corner {{ color: rgba(250, 250, 250, 0.5); }}
  a.st-bug-report-corner:hover {{ color: rgba(250, 250, 250, 0.92); }}
}}
</style>
<a class="st-bug-report-corner" href="{url}" title="Report a bug">Report a bug</a>"""


def render_bug_report_corner() -> None:
    """Show a single floating “Report a bug” control (see ``BUG_REPORT_FLOAT_CORNER``)."""
    st.markdown(bug_report_corner_html(), unsafe_allow_html=True)
