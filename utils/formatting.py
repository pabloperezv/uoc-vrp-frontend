"""Display-friendly formatting helpers."""

from __future__ import annotations


def format_meters(meters: float) -> str:
    if meters >= 1000:
        return f"{meters / 1000:.2f} km"
    return f"{meters:.0f} m"


def format_seconds(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def vehicle_color(index: int) -> str:
    """Return a stable, distinguishable color for the i-th vehicle."""

    palette = [
        "#2E86AB", "#E63946", "#06A77D", "#F4A261",
        "#9D4EDD", "#118AB2", "#EF476F", "#FFD166",
        "#073B4C", "#06D6A0", "#8338EC", "#FB5607",
    ]
    return palette[index % len(palette)]
