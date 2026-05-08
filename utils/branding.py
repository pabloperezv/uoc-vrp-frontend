"""UOC branding paths (logo, canonical web link)."""

from __future__ import annotations

from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent

UOC_LOGO_PATH: Path = _APP_ROOT / "assets" / "202-nova-marca-uoc.jpg"
FAVICON_PATH: Path = _APP_ROOT / "assets" / "favicon.png"
UOC_WEB_URL = "https://www.uoc.edu/"
