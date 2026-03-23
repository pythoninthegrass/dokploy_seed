import httpx
import json
import sys
from pathlib import Path


class DokployClient:
    """Thin httpx wrapper for Dokploy API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key},
            timeout=60.0,
        )

    def get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self.client.get(f"/api/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, payload: dict | None = None) -> dict:
        resp = self.client.post(f"/api/{path}", json=payload or {})
        resp.raise_for_status()
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
