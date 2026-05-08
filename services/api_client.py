"""Typed client for the FastAPI VRP backend."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests
import websocket

from utils.settings import FrontendSettings

OnJobEvent = Callable[[dict[str, Any]], None]


class BackendError(Exception):
    """Raised when the backend returns a non-2xx response or job failure."""

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


@dataclass
class VRPApiClient:
    settings: FrontendSettings

    def _headers_json(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.settings.backend_api_key:
            h["X-API-Key"] = self.settings.backend_api_key
        return h

    def _headers_get(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.settings.backend_api_key:
            h["X-API-Key"] = self.settings.backend_api_key
        return h

    def _ws_headers(self) -> list[str]:
        if self.settings.backend_api_key:
            return [f"X-API-Key: {self.settings.backend_api_key}"]
        return []

    def health(self) -> dict[str, Any]:
        r = requests.get(self.settings.health_endpoint, timeout=5)
        r.raise_for_status()
        return r.json()

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            r = requests.post(
                self.settings.jobs_endpoint,
                json=payload,
                headers=self._headers_json(),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise BackendError(f"Could not create job: {exc}") from exc

        if r.status_code == 202:
            return r.json()
        try:
            body = r.json()
        except ValueError:
            body = {"error": {"message": r.text[:500]}}
        if r.status_code == 404:
            raise BackendError(
                "Backend has no POST /api/v1/vrp/jobs route (redeploy the API image to enable async jobs). "
                f"The Solver will fall back to synchronous /solve when possible. Request URL: {self.settings.jobs_endpoint}",
                status_code=404,
                payload=body,
            )
        message = body.get("error", {}).get("message") or f"HTTP {r.status_code}"
        raise BackendError(message, status_code=r.status_code, payload=body)

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        url = f"{self.settings.jobs_endpoint}/{job_id}"
        try:
            r = requests.get(url, headers=self._headers_get(), timeout=15)
        except requests.RequestException as exc:
            raise BackendError(f"Could not poll job: {exc}") from exc
        if r.status_code == 200:
            return r.json()
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code == 404 and body.get("detail") == "Not Found":
            raise BackendError(
                "Backend returned 404 — no route matched (wrong BACKEND_URL or server not this API). "
                f"Tried: GET {url}",
                status_code=404,
                payload=body,
            )
        detail = body.get("detail") if isinstance(body.get("detail"), dict) else body
        msg = (detail or {}).get("message") if isinstance(detail, dict) else r.text
        raise BackendError(str(msg or f"HTTP {r.status_code}"), status_code=r.status_code, payload=body)

    def wait_for_job_via_websocket(
        self, ws_path: str, *, on_event: OnJobEvent | None = None
    ) -> dict[str, Any]:
        url = f"{self.settings.ws_base_url}{ws_path}"
        headers = self._ws_headers()
        try:
            ws = websocket.create_connection(
                url,
                header=headers or None,
                socket_timeout=60.0,
            )
        except Exception as exc:
            raise BackendError(f"WebSocket connection failed: {exc}") from exc

        deadline = time.time() + self.settings.job_max_wait_seconds
        try:
            while time.time() < deadline:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not raw:
                    continue
                data = json.loads(raw)
                if on_event:
                    on_event(data)
                t = data.get("type")
                if t == "complete":
                    return data["result"]
                if t == "error":
                    raise BackendError(
                        data.get("message", "Job failed"),
                        payload={"error": data},
                    )
                if t == "ping":
                    continue
            raise BackendError("Job timed out waiting on WebSocket.")
        finally:
            try:
                ws.close()
            except Exception:
                pass

    def wait_for_job_via_poll(
        self, job_id: str, *, on_event: OnJobEvent | None = None
    ) -> dict[str, Any]:
        deadline = time.time() + self.settings.job_max_wait_seconds
        while time.time() < deadline:
            st = self.get_job_status(job_id)
            if on_event:
                on_event({"type": "poll", "status": st.get("status"), "stage": st.get("stage")})
            if st.get("status") == "completed" and st.get("result") is not None:
                return st["result"]
            if st.get("status") == "failed":
                err = st.get("error") or {}
                raise BackendError(
                    err.get("message", "Job failed"),
                    payload=st,
                )
            time.sleep(0.35)
        raise BackendError("Job timed out (HTTP polling).")

    def solve_via_async_job(
        self, payload: dict[str, Any], *, on_event: OnJobEvent | None = None
    ) -> dict[str, Any]:
        """Create a job, wait on WebSocket, fall back to HTTP polling if needed."""
        try:
            meta = self.create_job(payload)
        except BackendError as exc:
            if exc.status_code == 404:
                if on_event:
                    on_event(
                        {
                            "type": "sync_fallback",
                            "detail": (
                                "Async /jobs is not available on this API (older server build). "
                                "Using synchronous POST /api/v1/vrp/solve."
                            ),
                        }
                    )
                return self.solve(payload)
            raise

        job_id = meta["job_id"]
        ws_path = meta["ws_path"]
        try:
            return self.wait_for_job_via_websocket(ws_path, on_event=on_event)
        except BackendError as exc:
            msg = str(exc)
            if "WebSocket connection failed" in msg or "Job timed out waiting on WebSocket" in msg:
                if on_event:
                    on_event({"type": "ws_fallback", "detail": msg})
                return self.wait_for_job_via_poll(job_id, on_event=on_event)
            raise
        except (OSError, ConnectionError, websocket.WebSocketException) as exc:
            if on_event:
                on_event({"type": "ws_fallback", "detail": str(exc)})
            return self.wait_for_job_via_poll(job_id, on_event=on_event)

    def solve(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Synchronous single POST /solve (short problems only)."""
        try:
            r = requests.post(
                self.settings.solve_endpoint,
                json=payload,
                headers=self._headers_json(),
                timeout=self.settings.request_timeout_seconds,
            )
        except requests.Timeout as exc:
            raise BackendError(
                f"Backend did not respond within {self.settings.request_timeout_seconds}s. "
                "Use async jobs or shorten the solver time limit."
            ) from exc
        except requests.RequestException as exc:
            raise BackendError(f"Could not reach backend: {exc}") from exc

        if r.status_code == 200:
            return r.json()

        try:
            body = r.json()
        except ValueError:
            body = {"error": {"message": r.text[:500]}}
        message = body.get("error", {}).get("message") or f"HTTP {r.status_code}"
        raise BackendError(message, status_code=r.status_code, payload=body)
