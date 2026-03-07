# Changelog

## [0.2.0](https://github.com/pythoninthegrass/dokploy_seed/compare/dokploy-seed-v0.1.0...dokploy-seed-v0.2.0) (2026-03-07)


### Features

* add `check` subcommand for pre-flight validation ([91c0868](https://github.com/pythoninthegrass/dokploy_seed/commit/91c08686a2278526e4fd0c331fb1e68cd3ef2b40))
* **cli:** add `import` subcommand to adopt existing Dokploy projects ([9ead2d7](https://github.com/pythoninthegrass/dokploy_seed/commit/9ead2d7fdcee92ef4ddf0876595d57cb9d935bb8))
* **cli:** add unified `deploy` subcommand, rename old deploy to `trigger` ([d489377](https://github.com/pythoninthegrass/dokploy_seed/commit/d489377291af0a832375a3efcf36782f02b773f6))
* implement all 7 prod gaps in dokploy.py (buildType, domain.path, autoDeploy, watchPaths, replicas, triggerType, buildPath) ([970f9ea](https://github.com/pythoninthegrass/dokploy_seed/commit/970f9eaa85c6abe64f52a0d8074e32d0afc16ff3))
* **setup:** auto-select GitHub provider by matching owner ([edefe14](https://github.com/pythoninthegrass/dokploy_seed/commit/edefe14aeb83b912e75926be179e997473244491))


### Bug Fixes

* **api:** always send dockerContextPath/dockerBuildStage in saveBuildType ([31b8037](https://github.com/pythoninthegrass/dokploy_seed/commit/31b8037074f46d323ef85329cc3290da0e09bf82))
* **api:** update dokploy.py for Dokploy v0.28.4 compatibility ([50895a8](https://github.com/pythoninthegrass/dokploy_seed/commit/50895a8b2a484713a27b52ab8600381d3e8c8bc2))
* apply principle of least privilege to release-please.yml permissions ([fa04d9b](https://github.com/pythoninthegrass/dokploy_seed/commit/fa04d9b0e2527fe38d6e40e1cde75e450228d32a))
* **test:** add pytestmark to test_unit.py and test_integration.py ([9d89eed](https://github.com/pythoninthegrass/dokploy_seed/commit/9d89eedc0d21bd21db00520f2d8b7827d724641f))
* **test:** assert domain fields against fixture, not hardcoded values ([dfba11a](https://github.com/pythoninthegrass/dokploy_seed/commit/dfba11a60ef718b1ed9df370dd983ab49293d02a))
* **test:** monkeypatch decouple config instead of os.environ ([5768053](https://github.com/pythoninthegrass/dokploy_seed/commit/5768053a2c328d3e7a8d867533394f949c521f88))


### Documentation

* add backlog tasks ([e2d70bf](https://github.com/pythoninthegrass/dokploy_seed/commit/e2d70bf1dabae51550d4738ffc52782fe14d3fc1))
* Fix GitHub issues link in security response plan ([ba0f40b](https://github.com/pythoninthegrass/dokploy_seed/commit/ba0f40bb98726507b45c7036b173ce80300269cf))
* update backlog tasks ([afa734e](https://github.com/pythoninthegrass/dokploy_seed/commit/afa734eae63cda625e3b147fdb79a73c475340ea))
* update llm instrx ([191ce50](https://github.com/pythoninthegrass/dokploy_seed/commit/191ce5060070db8dd70e049d0485cf17908e6880))
* update llm instrx ([65f41f6](https://github.com/pythoninthegrass/dokploy_seed/commit/65f41f69e76c3e14c97853ebcebcfd23578bba68))
