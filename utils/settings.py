"""Frontend runtime settings.

Reads values from Streamlit ``st.secrets`` (preferred for Streamlit Cloud) and
falls back to environment variables for local development.

``BACKEND_URL`` must be the API **origin** only (``http(s)://host[:port]``).
If ``/api``, ``/api/v1``, or ``/api/v1/vrp`` is appended by mistake, it is
stripped so paths like ``…/api/v1/api/v1/…`` (404) are avoided.

``OSRM_BASE_URL`` (optional) is the OSRM server used to draw **road-following**
polylines on the solution map. Defaults to ``http://127.0.0.1:5000`` when unset.
Set to an empty string to disable and use straight-line segments only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


def _normalize_backend_origin(url: str) -> str:
    """Scheme + host + port only; strip accidental API path suffixes."""
    u = url.strip().rstrip("/")
    if not u:
        return "http://localhost:8010"
    lowered = u.lower()
    for suffix in ("/api/v1/vrp", "/api/v1", "/api"):
        if lowered.endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
            lowered = u.lower()
    return u or "http://localhost:8010"


@dataclass(frozen=True)
class FrontendSettings:
    backend_url: str
    backend_api_key: str | None
    request_timeout_seconds: float
    job_max_wait_seconds: float
    osrm_base_url: str | None

    @property
    def api_base(self) -> str:
        return self.backend_url.rstrip("/")

    @property
    def solve_endpoint(self) -> str:
        return f"{self.api_base}/api/v1/vrp/solve"

    @property
    def health_endpoint(self) -> str:
        return f"{self.api_base}/api/v1/health"

    @property
    def jobs_endpoint(self) -> str:
        return f"{self.api_base}/api/v1/vrp/jobs"

    @property
    def ws_base_url(self) -> str:
        """WebSocket origin for async job streams (matches ``BACKEND_URL`` scheme)."""
        if self.api_base.startswith("https://"):
            return "wss://" + self.api_base[8:]
        if self.api_base.startswith("http://"):
            return "ws://" + self.api_base[7:]
        return self.api_base


def _read(key: str, default: str | None = None) -> str | None:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        pass
    return os.getenv(key, default)


def _osrm_base_url() -> str | None:
    """OSRM origin for map polylines. Empty string disables; unset defaults to local :5000."""
    raw = _read("OSRM_BASE_URL", None)
    if raw is None:
        return "http://127.0.0.1:5000"
    stripped = raw.strip()
    if not stripped:
        return None
    return stripped.rstrip("/")


@st.cache_resource(show_spinner=False)
def get_settings() -> FrontendSettings:
    return FrontendSettings(
        backend_url=_normalize_backend_origin(
            _read("BACKEND_URL", "http://localhost:8010") or "http://localhost:8010"
        ),
        backend_api_key=_read("BACKEND_API_KEY", "") or None,
        request_timeout_seconds=float(_read("REQUEST_TIMEOUT_SECONDS", "120") or 120),
        job_max_wait_seconds=float(_read("JOB_MAX_WAIT_SECONDS", "600") or 600),
        osrm_base_url=_osrm_base_url(),
    )
