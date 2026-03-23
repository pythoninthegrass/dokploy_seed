import os
import sys
from decouple import Config, RepositoryEmpty, RepositoryEnv
from pathlib import Path


def _build_config() -> Config:
    """Build a decouple Config from the resolved .env path.

    Honors the ``DOTENV_FILE`` environment variable to override the default
    path, following the python-decouple convention.
    """
    env_file = Path(os.environ.get("DOTENV_FILE", str(Path.cwd() / ".env")))
    if env_file.is_file():
        return Config(RepositoryEnv(str(env_file)))
    return Config(RepositoryEmpty())


config = _build_config()


def find_repo_root() -> Path:
    """Walk up from cwd looking for dokploy.yml."""
    current = Path.cwd()
    while True:
        if (current / "dokploy.yml").exists():
            return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root without finding config
            print("ERROR: Could not find dokploy.yml in any parent directory.")
            sys.exit(1)
        current = parent
