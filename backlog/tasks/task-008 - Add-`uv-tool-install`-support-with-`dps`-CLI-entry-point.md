---
id: TASK-008
title: Add `uv tool install` support with `dps` CLI entry point
status: Done
assignee: []
created_date: '2026-03-07 06:42'
updated_date: '2026-03-09 22:07'
labels:
  - enhancement
  - cli
dependencies: []
references:
  - dokploy.py
  - AGENTS.md
  - README.md
  - ~/git/rsl/pyproject.toml
  - ~/git/rsl/main.py
  - ~/git/rsl/src/rsl/__init__.py
  - ~/git/rsl/src/rsl/main.py (symlink)
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add `pyproject.toml` with `uv_build` backend and `dps` entry point so the project can be installed globally via `uv tool install git+https://github.com/pythoninthegrass/dokploy_seed`. Change path resolution from `__file__`-based to `cwd`-based so the tool finds `dokploy.yml` and `.dokploy-state/` relative to where it's invoked. Update all project docs. Keep backward compat with `uv run --script dokploy.py`.

## Implementation Details

1. **Add `pyproject.toml`** at repo root:
   - `name = "dokploy-seed"`
   - `[project.scripts] dps = "dokploy:main"`
   - `build-system`: `uv_build`
   - Dependencies mirrored from PEP 723 inline metadata in `dokploy.py`
   - `requires-python = ">=3.13,<3.14"`

2. **Change `find_repo_root()`** (`dokploy.py:37-48`):
   - Replace `Path(__file__).resolve().parent` with `Path.cwd()`
   - Both modes work: `uv run --script` users are already in the repo; `dps` users are in their project dir

3. **Change `cmd_check` call** (`dokploy.py:714`):
   - Replace `Path(__file__).resolve().parent` with `Path.cwd()`

4. **Keep PEP 723 inline metadata** in `dokploy.py` for `uv run --script` backward compat

5. **Update AGENTS.md**:
   - Line 5: Overview — mention installable via `uv tool install` in addition to "copied into any project repo"
   - Lines 9-11: Tech stack — note dual mode (PEP 723 inline script + `pyproject.toml` for tool install)
   - Lines 15-24: Project structure — add `pyproject.toml` entry
   - Lines 28-36: Key Commands — add `dps` commands alongside `uv run --script` examples

6. **Update README.md**:
   - Line 27: Prerequisites — mention `uv tool install` as alternative installation method
   - Lines 30-53: Quick Start — add installation via `uv tool install git+https://github.com/pythoninthegrass/dokploy_seed`, show `dps` commands
   - Lines 76-86: Environment Selection — show `dps` examples alongside `uv run --script`
   - Lines 123-127: Config File Discovery details — update to reflect cwd-based resolution
   - Lines 151-159: Adding to an Existing Project — add `uv tool install` as a simpler alternative to copying files

7. **docs/ files** — no changes needed (api-notes.md, configuration.md, testing.md don't reference invocation patterns)

## Key Files

- `dokploy.py` — `find_repo_root()` (line 37), `main()` (line 698)
- `pyproject.toml` — new file
- `AGENTS.md` — overview, tech stack, structure, key commands
- `README.md` — prerequisites, quick start, environment selection, config discovery, adding to existing project
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `uv tool install git+https://github.com/pythoninthegrass/dokploy_seed` succeeds
- [x] #2 `dps --help` works from any directory
- [x] #3 `dps --env prod setup` works from a directory containing `dokploy.yml`
- [x] #4 `uv run --script dokploy.py setup` still works (backward compat)
- [x] #5 `.dokploy-state/` and `dokploy.yml` resolved from cwd
- [x] #6 AGENTS.md updated with dual-mode info and `dps` commands
- [x] #7 README.md updated with installation, quick start, and usage for `dps`
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan (based on `rsl` reference implementation)

### Reference: `~/git/rsl` Pattern

The `rsl` project uses a **symlink strategy** to support both `uv run --script main.py` and `uv tool install`:

```
rsl/
├── main.py                    # PEP 723 inline script (standalone)
├── pyproject.toml             # build config + entry point
└── src/rsl/
    ├── __init__.py            # re-exports main()
    └── main.py -> ../../main.py  # symlink to root script
```

Key details:
- `[project.scripts] rsl = "rsl:main"` — entry point calls `main()` from `rsl` package
- `src/rsl/__init__.py` does `from rsl.main import main; __all__ = ["main"]`
- `src/rsl/main.py` is a **relative symlink** (`../../main.py`) to the root script
- `[build-system] requires = ["uv_build>=0.10.2,<0.11.0"]`, `build-backend = "uv_build"`
- Single source of truth: all logic lives in root `main.py`

### Steps for `dokploy_seed`

#### 1. Create `src/dokploy_seed/` directory structure

```
src/dokploy_seed/
├── __init__.py
└── main.py -> ../../dokploy.py   # symlink (not main.py — our script is dokploy.py)
```

`src/dokploy_seed/__init__.py`:
```python
from dokploy_seed.main import main

__all__ = ["main"]
```

Symlink:
```bash
ln -s ../../dokploy.py src/dokploy_seed/main.py
```

#### 2. Create `pyproject.toml`

```toml
[project]
name = "dokploy-seed"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
    "httpx>=0.28.1,<1.0",
    "python-decouple>=3.8",
    "pyyaml>=6.0.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0.2",
    "ruff>=0.15.5",
]

[project.scripts]
dps = "dokploy_seed:main"

[build-system]
requires = ["uv_build>=0.10.2,<0.11.0"]
build-backend = "uv_build"
```

Note: dependencies must mirror PEP 723 inline metadata in `dokploy.py`.

#### 3. Update `dokploy.py` path resolution

- `find_repo_root()` (line ~37): change `Path(__file__).resolve().parent` to `Path.cwd()`
- `cmd_check` call (line ~714): same change
- Both modes work: script users are already in repo dir; `dps` users invoke from their project dir

#### 4. Keep PEP 723 inline metadata in `dokploy.py`

No changes needed — backward compat with `uv run --script dokploy.py` is preserved.

#### 5. Update docs (AGENTS.md, README.md)

Per existing task description — add dual-mode info and `dps` commands.

### Key Difference from `rsl`

- `rsl` symlinks `src/rsl/main.py -> ../../main.py`
- We symlink `src/dokploy_seed/main.py -> ../../dokploy.py` (different filename)
- Package name `dokploy-seed` with underscore module `dokploy_seed` (PEP 503 normalization)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Reference Implementation

The `rsl` project at `~/git/rsl` is the reference for this pattern. It was built first and proves the symlink + `uv_build` approach works.

### Symlink Detail

The symlink is **relative** (`../../dokploy.py`), not absolute. This ensures it works across clones and machines. Git tracks symlinks by default, so this will work for anyone who clones the repo.

### Why symlink instead of import?

- Avoids code duplication between standalone script and package
- PEP 723 inline metadata stays in the root script (required for `uv run --script`)
- `pyproject.toml` metadata stays in build config (required for `uv tool install`)
- Single file contains all logic — no split across modules

### `uv_build` backend

The `uv_build` backend is purpose-built for uv and handles the `src/` layout natively. It finds the package in `src/dokploy_seed/` and builds a wheel with the entry point.

### Testing concern

When installed as a tool, `dokploy.py`'s PEP 723 script block (the `# /// script` comment) is harmless — Python ignores it as a comment. The `if __name__ == "__main__"` guard in `main()` may need review to ensure the entry point calls `main()` directly without going through the guard.

## Verification Results

- `uv tool install /Users/lance/git/dokploy_seed` — installed `dps` executable
- `dps --help` — works from any directory
- `uv run --script dokploy.py --help` — backward compat confirmed
- All 132 tests pass (5 e2e deselected)
- ruff format clean, markdownlint clean
- AC #3 (`dps --env prod setup` from a directory with `dokploy.yml`) not tested live (requires Dokploy server)

## .env Discovery Fix

`python-decouple`'s `AutoConfig` walks up from the calling module's `__file__` to find `.env`. When installed as a uv tool, the module lives in `~/.local/share/uv/tools/`, so it never finds the user's `.env`.

Fix: replaced `from decouple import config` with a custom `_build_config()` that uses `Config(RepositoryEnv(cwd / '.env'))`. Falls back to `RepositoryEmpty()` (env vars only) when no `.env` exists in cwd.

## AC #3 Verified

- Created a test `dokploy.yml` with a minimal nginx:alpine Docker app
- `dps --env prod setup` created the project successfully
- `dps --env prod status` showed the app as idle
- `dps --env prod destroy` cleaned up
- Restored original `dokploy.yml` afterward
<!-- SECTION:NOTES:END -->
