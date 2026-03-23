---
id: TASK-023
title: Add API retry with exponential backoff
status: To Do
assignee: []
created_date: '2026-03-23 18:05'
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
- [ ] #1 API calls retry on 429 and 5xx status codes
- [ ] #2 Exponential backoff between retries (e.g. 1s, 2s, 4s)
- [ ] #3 Max retry count is configurable or defaults to 3
- [ ] #4 Non-retryable errors (4xx except 429) fail immediately
<!-- AC:END -->
