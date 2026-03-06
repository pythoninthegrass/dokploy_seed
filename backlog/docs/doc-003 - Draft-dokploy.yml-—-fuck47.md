---
id: doc-003
title: Draft dokploy.yml — fuck47
type: other
created_date: '2026-03-06 15:11'
---
# Draft dokploy.yml for fuck47

Reproduces the prod "fuck47" project (static site) on Dokploy.

## Blockers — cannot fully reproduce

- `buildType: "static"` — dokploy.py hardcodes "dockerfile"; must change buildType manually via API/UI after setup
- `domain.path: "/docs"` — not in schema; must set path manually in Dokploy UI after domain creation
- `autoDeploy: true` — not yet in schema

## Config

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/pythoninthegrass/dokploy_seed/main/schemas/dokploy.schema.json

project:
  name: fuck47
  description: fuck47 static site — dev.fuckfortyseven.org

  deploy_order:
    - [app]

github:
  owner: pythoninthegrass
  repository: fuck47
  branch: main

environments:
  prod:
    apps:
      app:
        domain:
          host: dev.fuckfortyseven.org
          port: 80
          https: true
          certificateType: letsencrypt

apps:
  - name: app
    source: github
```
