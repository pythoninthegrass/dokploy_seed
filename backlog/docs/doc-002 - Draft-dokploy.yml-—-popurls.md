---
id: doc-002
title: Draft dokploy.yml — popurls
type: other
created_date: '2026-03-06 15:11'
---
# Draft dokploy.yml for popurls

Reproduces the prod "popurls" project (Glance dashboard) on Dokploy.

## Unsupported settings (require manual config)

- `autoDeploy: true` — not yet in schema
- `watchPaths: ["config/**", "assets/**", "Dockerfile", "^(?!.*\\.md$).*$"]` — must be set via API or Dokploy UI

## Config

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/pythoninthegrass/icarus/main/schemas/dokploy.schema.json

project:
  name: popurls
  description: Glance dashboard — popurls.xyz

  env_targets: [app]

  deploy_order:
    - [app]

github:
  owner: pythoninthegrass
  repository: glance
  branch: main

environments:
  prod:
    apps:
      app:
        domain:
          host: popurls.xyz
          port: 8080
          https: true
          certificateType: letsencrypt

apps:
  - name: app
    source: github
```
