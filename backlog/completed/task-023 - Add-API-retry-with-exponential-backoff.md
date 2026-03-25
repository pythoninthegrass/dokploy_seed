---
id: TASK-023
title: Add API retry with exponential backoff
status: Done
assignee: []
created_date: '2026-03-23 18:05'
updated_date: '2026-03-24 20:27'
labels:
  - gap-analysis
  - reliability
milestone: m-0
dependencies: []
references:
  - main.py
priority: medium
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Icarus has no retry mechanism — transient API failures (429 rate limits, 5xx server errors) cause hard stops. The TF provider implements exponential backoff retry logic (3 retries on 429/5xx). Add a retry wrapper around API calls with configurable max retries and backoff.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 API calls retry on 429 and 5xx status codes
- [x] #2 Exponential backoff between retries (e.g. 1s, 2s, 4s)
- [x] #3 Max retry count is configurable or defaults to 3
- [x] #4 Non-retryable errors (4xx except 429) fail immediately
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added retry with exponential backoff to `DokployClient` in `src/icarus/client.py`. New `_request()` method retries on 429 and 5xx status codes with 1s/2s/4s backoff. Non-retryable 4xx errors fail immediately. `max_retries` parameter defaults to 3, configurable via constructor. 8 unit tests added covering all acceptance criteria.
<!-- SECTION:FINAL_SUMMARY:END -->
