import httpx
import json
import sys
import time
from pathlib import Path


class DokployClient:
    """Thin httpx wrapper for Dokploy API."""

    def __init__(self, base_url: str, api_key: str, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key},
            timeout=60.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Send an HTTP request with retry on 429/5xx and exponential backoff."""
        url = f"/api/{path}"
        last_exc: httpx.HTTPStatusError | None = None
        for attempt in range(self.max_retries + 1):
            resp = self.client.request(method, url, **kwargs)
            if resp.status_code < 400:
                return resp
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = httpx.HTTPStatusError(
                    message=f"{resp.status_code} {resp.reason_phrase}",
                    request=resp.request,
                    response=resp,
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise last_exc
            # Non-retryable 4xx — fail immediately
            resp.raise_for_status()
        raise last_exc  # type: ignore[misc]

    def get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self._request("GET", path, params=params)
        return resp.json()

    def post(self, path: str, payload: dict | None = None) -> dict:
        resp = self._request("POST", path, json=payload or {})
        if not resp.content:
            return {}
        return resp.json()


def validate_state(client: DokployClient, state: dict) -> bool:
    """Check if the project in state still exists on the server.

    Returns True if valid or if the server can't be reached (assume valid).
    Returns False if the project is confirmed gone.
    """
    try:
        projects = client.get("project.all")
    except httpx.HTTPStatusError:
        return True
    return any(p["projectId"] == state["projectId"] for p in projects)


def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        print(f"ERROR: State file not found: {state_file}")
        print("Run 'setup' first.")
        sys.exit(1)
    return json.loads(state_file.read_text())


def save_state(state: dict, state_file: Path, *, quiet: bool = False) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2) + "\n")
    if not quiet:
        print(f"State saved to {state_file}")
