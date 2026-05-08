# UOC VRP Frontend

Streamlit application for interacting with the [UOC VRP backend](../uoc-vrp-backend).
Upload a CSV of customers, configure the fleet, run an optimisation and inspect
the resulting routes on an interactive Folium map.

---

## Project layout

```
.
├── app.py                  # Landing page (multi-page entrypoint)
├── pages/
│   ├── 1_Solver.py         # Main page: upload + solve + visualise
│   └── 2_About.py
├── components/
│   ├── sidebar.py          # Sidebar widgets -> VRPParameters dataclass
│   ├── map_view.py         # Folium map renderers
│   └── metrics.py          # KPI cards + per-route tables
├── services/
│   ├── api_client.py       # Typed wrapper around the FastAPI backend
│   └── csv_loader.py       # CSV parsing + validation + payload builder
├── utils/
│   ├── settings.py         # Reads st.secrets / env vars
│   └── formatting.py       # Human-friendly distance/time formatting
├── sample_data/
│   └── madrid_sample.csv
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
└── requirements.txt
```

The structure follows the **same separation principle** as the backend:
`pages` orchestrate, `components` render, `services` talk to external systems,
`utils` are pure functions.

---

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit secrets.toml: BACKEND_URL = "http://localhost:8010"  (origin only; no /api/v1)
# optional: OSRM_BASE_URL for road polylines on the map (defaults to http://127.0.0.1:5000)

streamlit run app.py
```

Open <http://localhost:8501> in your browser.

---

## Deployment to Streamlit Community Cloud

1. Push this repository to GitHub.
2. On <https://streamlit.io/cloud>, create a new app and point it at:
   - **Repository**: your `uoc-vrp-frontend` repo
   - **Branch**: `main`
   - **Main file**: `app.py`
3. In the **Secrets** panel, paste:
   ```toml
   # Public URL of the FastAPI process (scheme + host, optional port only).
   BACKEND_URL = "https://vrp-api.example.com"
   BACKEND_API_KEY = "..."         # optional
   REQUEST_TIMEOUT_SECONDS = 120
   ```
4. Make sure your backend `CORS_ALLOWED_ORIGINS` includes the URL Streamlit
   Cloud assigns to your app (e.g. `https://uoc-vrp.streamlit.app`).

### Pre-deployment checklist

- [ ] Backend exposed over **HTTPS** (Streamlit Cloud refuses mixed content).
- [ ] CORS configured on the backend with the exact frontend URL.
- [ ] Dependencies pinned in `requirements.txt`.
- [ ] No secrets committed; everything sensitive lives in Streamlit Secrets.

---

## CSV format

| Column     | Required | Type   | Notes                              |
|------------|----------|--------|------------------------------------|
| `id`       | yes      | string | Unique customer id.                |
| `name`     | no       | string | Defaults to `id`.                  |
| `latitude` | yes      | float  | WGS84, in `[-90, 90]`.             |
| `longitude`| yes      | float  | WGS84, in `[-180, 180]`.           |
| `demand`   | no       | int    | Integer units. Defaults to `1`.    |

A working sample is provided at `sample_data/madrid_sample.csv`.

---

## Architecture decisions (frontend)

- **Multi-page app**: `pages/` is auto-discovered by Streamlit. Each page is a
  thin orchestrator that delegates to `components` and `services`.
- **Service classes own all I/O**: the UI never imports `requests` directly,
  which keeps Streamlit reruns cheap and components testable in isolation.
- **Dataclasses over dicts**: parameters flow through typed structures
  (`VRPParameters`, `FrontendSettings`) for clarity and IDE support.
- **Folium over PyDeck** by default: lighter, easier popups, no GPU dependency.
  PyDeck remains a great upgrade path for very large fleets.
- **`st.cache_resource`** is used on `get_settings`; do **not** cache the API
  client itself across reruns — the underlying socket pool is not always
  thread-safe with Streamlit's reruns.
