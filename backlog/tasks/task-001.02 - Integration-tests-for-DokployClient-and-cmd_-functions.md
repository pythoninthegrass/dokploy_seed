---
id: TASK-001.02
title: Integration tests for DokployClient and cmd_* functions
status: In Progress
assignee: []
created_date: '2026-03-06 08:13'
updated_date: '2026-03-06 08:14'
labels:
  - testing
  - integration-tests
dependencies: []
references:
  - 'dokploy.py:167-557'
  - docs/api-notes.md
  - examples/web-app/dokploy.yml
documentation:
  - 'https://lundberg.github.io/respx/'
parent_task_id: TASK-001
priority: high
ordinal: 750
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write pytest integration tests for `DokployClient` and the `cmd_*` command functions in `dokploy.py`. These tests mock the Dokploy HTTP API using `respx` (the httpx-native mock library) and verify that the commands orchestrate API calls correctly.

**Components to test:**

1. **`DokployClient`** (line 167)
   - `__init__`: verify base_url trailing slash stripped, headers set, timeout configured
   - `get(path, params)`: verify URL construction (`/api/{path}`), params forwarded, JSON parsed
   - `post(path, payload)`: verify URL construction, JSON body sent, empty response handled (returns `{}`)
   - Error handling: verify `httpx.HTTPStatusError` raised on 4xx/5xx

2. **`cmd_check(repo_root)`** (line 204)
   - Mock env vars (DOKPLOY_API_KEY, DOKPLOY_URL) via monkeypatch
   - Mock httpx.get for server reachability and API key check
   - Test all-pass scenario, missing API key, unreachable server, invalid API key, missing config file
   - Verify exit code 0 on success, 1 on failure

3. **`cmd_setup(client, cfg, state_file)`** (line 328)
   - Mock API responses: `project.create` → project/environment IDs, `github.githubProviders` → githubId, `application.create` → applicationId/appName, provider/buildType/update/domain calls
   - Verify correct API call sequence and payloads
   - Verify state file written with correct structure
   - Test error: state file already exists → sys.exit

4. **`cmd_env(client, cfg, state_file, repo_root)`** (line 469)
   - Create mock state file and .env file
   - Verify `application.saveEnvironment` called with filtered env content
   - Verify per-app custom env resolved and pushed
   - Test missing .env file → sys.exit

5. **`cmd_deploy(client, cfg, state_file)`** (line 521)
   - Verify `application.deploy` called in wave order
   - Verify correct applicationIds from state

6. **`cmd_status(client, state_file)`** (line 536)
   - Mock `application.one` responses with status
   - Verify output formatting

7. **`cmd_destroy(client, state_file)`** (line 547)
   - Verify `project.remove` called with correct projectId
   - Verify state file deleted

8. **Full pipeline test**: `setup → env → deploy → status → destroy` sequence with a realistic config (use `examples/web-app/dokploy.yml`), verifying state file lifecycle and API call ordering across all commands.

**Test infrastructure:**
- Place tests in `tests/test_integration.py`
- Use `respx` for httpx mocking (add to test dependencies)
- Use `tmp_path` for state files and .env files
- Create fixtures for: mock DokployClient, sample configs, sample state dicts, respx routers with canned API responses
- Share fixtures with unit tests via `tests/conftest.py`

**Dependencies:** pytest, pytest-cov, respx

**Key files:**
- `dokploy.py:167-557` — DokployClient class and all cmd_* functions
- `docs/api-notes.md` — API quirks (repository name format, saveBuildType strings, project.remove not project.delete, empty deploy response)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 DokployClient get/post methods tested with respx-mocked responses
- [ ] #2 Each cmd_* function has at least one happy-path and one error-path test
- [ ] #3 Full pipeline test (setup→env→deploy→status→destroy) passes with mocked API
- [ ] #4 API call payloads verified against docs/api-notes.md quirks (e.g. repository name format, saveBuildType explicit strings)
- [ ] #5 State file lifecycle verified: created by setup, read by env/deploy/status, deleted by destroy
- [ ] #6 All tests pass with `uv run pytest tests/test_integration.py`
<!-- AC:END -->
