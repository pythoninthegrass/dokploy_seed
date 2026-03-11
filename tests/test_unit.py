"""Unit tests for pure functions in main.py."""

import importlib.util
import json
import pytest
import sys
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import main.py as a module despite it being a PEP 723 script.
_SCRIPT = Path(__file__).resolve().parent.parent / "main.py"
_spec = importlib.util.spec_from_file_location("dokploy", _SCRIPT)
dokploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dokploy)

pytestmark = pytest.mark.unit


class TestFindRepoRoot:
    def test_finds_repo_root(self, tmp_path, monkeypatch):
        """find_repo_root walks up and returns the dir containing dokploy.yml."""
        (tmp_path / "dokploy.yml").write_text("project: {}")
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        assert dokploy.find_repo_root() == tmp_path

    def test_exits_when_not_found(self, tmp_path, monkeypatch):
        """find_repo_root exits when no dokploy.yml is found."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            dokploy.find_repo_root()


class TestLoadConfig:
    def test_loads_valid_yaml(self, tmp_path, minimal_config):
        cfg_file = tmp_path / "dokploy.yml"
        cfg_file.write_text(yaml.dump(minimal_config))
        result = dokploy.load_config(tmp_path)
        assert result["project"]["name"] == "my-app"

    def test_exits_on_missing_file(self, tmp_path):
        with pytest.raises(SystemExit):
            dokploy.load_config(tmp_path)


class TestValidateConfig:
    def test_valid_config_passes(self, web_app_config):
        # Should not raise
        dokploy.validate_config(web_app_config)

    def test_unknown_app_in_env_targets_exits(self, minimal_config):
        minimal_config["project"]["env_targets"] = ["nonexistent"]
        with pytest.raises(SystemExit):
            dokploy.validate_config(minimal_config)

    def test_unknown_app_in_deploy_order_exits(self, minimal_config):
        minimal_config["project"]["deploy_order"] = [["nonexistent"]]
        with pytest.raises(SystemExit):
            dokploy.validate_config(minimal_config)

    def test_missing_github_section_exits(self, minimal_config):
        minimal_config["apps"].append({"name": "api", "source": "github"})
        minimal_config["project"]["deploy_order"] = [["app", "api"]]
        with pytest.raises(SystemExit):
            dokploy.validate_config(minimal_config)

    def test_github_section_present_passes(self, minimal_config):
        minimal_config["apps"].append({"name": "api", "source": "github"})
        minimal_config["project"]["deploy_order"] = [["app", "api"]]
        minimal_config["github"] = {
            "owner": "org",
            "repository": "repo",
            "branch": "main",
        }
        dokploy.validate_config(minimal_config)


class TestValidateEnvReferences:
    def test_valid_refs_pass(self, web_app_config):
        dokploy.validate_env_references(web_app_config)

    def test_unknown_app_in_env_overrides_exits(self, minimal_config):
        minimal_config["environments"] = {"prod": {"apps": {"bogus": {"dockerImage": "x"}}}}
        with pytest.raises(SystemExit):
            dokploy.validate_env_references(minimal_config)

    def test_no_environments_passes(self, minimal_config):
        minimal_config.pop("environments", None)
        dokploy.validate_env_references(minimal_config)


class TestMergeEnvOverrides:
    def test_github_overrides_merge(self, web_app_config):
        merged = dokploy.merge_env_overrides(web_app_config, "dev")
        assert merged["github"]["branch"] == "develop"
        # Owner should be preserved from base
        assert merged["github"]["owner"] == "your-org"

    def test_per_app_overrides_merge(self, web_app_config):
        merged = dokploy.merge_env_overrides(web_app_config, "prod")
        web = next(a for a in merged["apps"] if a["name"] == "web")
        assert web["domain"]["host"] == "app.example.com"

    def test_missing_env_returns_base(self, minimal_config):
        merged = dokploy.merge_env_overrides(minimal_config, "nonexistent")
        assert merged["project"]["name"] == "my-app"
        assert "environments" not in merged

    def test_original_config_unchanged(self, web_app_config):
        import copy

        original = copy.deepcopy(web_app_config)
        dokploy.merge_env_overrides(web_app_config, "dev")
        assert web_app_config == original


class TestResolveRefs:
    def test_single_ref(self, sample_state):
        result = dokploy.resolve_refs("redis://{redis}:6379/0", sample_state)
        assert result == "redis://redis-abc123:6379/0"

    def test_multiple_refs(self, sample_state):
        result = dokploy.resolve_refs("{redis} and {web}", sample_state)
        assert result == "redis-abc123 and web-def456"

    def test_unknown_ref_left_as_is(self, sample_state):
        result = dokploy.resolve_refs("{unknown}", sample_state)
        assert result == "{unknown}"

    def test_no_refs_unchanged(self, sample_state):
        result = dokploy.resolve_refs("plain string", sample_state)
        assert result == "plain string"


class TestGetEnvExcludePrefixes:
    def test_defaults_only(self, monkeypatch):
        monkeypatch.delenv("ENV_EXCLUDE_PREFIXES", raising=False)
        prefixes = dokploy.get_env_exclude_prefixes()
        assert "COMPOSE_" in prefixes
        assert "DOKPLOY_" in prefixes

    def test_with_extras(self, monkeypatch):
        monkeypatch.setenv("ENV_EXCLUDE_PREFIXES", "MY_SECRET_,INTERNAL_")
        prefixes = dokploy.get_env_exclude_prefixes()
        assert "MY_SECRET_" in prefixes
        assert "INTERNAL_" in prefixes
        # Defaults still present
        assert "COMPOSE_" in prefixes

    def test_empty_extras(self, monkeypatch):
        monkeypatch.setenv("ENV_EXCLUDE_PREFIXES", "")
        prefixes = dokploy.get_env_exclude_prefixes()
        assert prefixes == dokploy.DEFAULT_ENV_EXCLUDE_PREFIXES


class TestFilterEnv:
    def test_comments_removed(self):
        content = "# comment\nFOO=bar\n"
        result = dokploy.filter_env(content, [])
        assert "# comment" not in result
        assert "FOO=bar" in result

    def test_blank_lines_removed(self):
        content = "\n\nFOO=bar\n\n"
        result = dokploy.filter_env(content, [])
        assert result == "FOO=bar\n"

    def test_excluded_prefixes_filtered(self):
        content = "COMPOSE_FILE=x\nAPP_URL=y\n"
        result = dokploy.filter_env(content, ["COMPOSE_"])
        assert "COMPOSE_FILE" not in result
        assert "APP_URL=y" in result

    def test_valid_lines_kept(self):
        content = "A=1\nB=2\nC=3\n"
        result = dokploy.filter_env(content, [])
        assert result == "A=1\nB=2\nC=3\n"

    def test_trailing_newline(self):
        content = "A=1"
        result = dokploy.filter_env(content, [])
        assert result.endswith("\n")

    def test_empty_after_filtering(self):
        content = "# just a comment\n"
        result = dokploy.filter_env(content, [])
        assert result == ""


class TestLoadSaveState:
    def test_round_trip(self, tmp_path, sample_state):
        state_file = tmp_path / ".dokploy-state" / "test.json"
        dokploy.save_state(sample_state, state_file)
        loaded = dokploy.load_state(state_file)
        assert loaded == sample_state

    def test_load_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            dokploy.load_state(tmp_path / "nonexistent.json")

    def test_save_creates_directory(self, tmp_path, sample_state):
        state_file = tmp_path / "deep" / "nested" / "state.json"
        dokploy.save_state(sample_state, state_file)
        assert state_file.exists()
        assert json.loads(state_file.read_text()) == sample_state


class TestArgparse:
    def test_valid_commands(self):
        for cmd in ["check", "setup", "env", "deploy", "trigger", "status", "destroy", "import"]:
            args = dokploy.argparse.ArgumentParser()
            args.add_argument("--env", default=None)
            args.add_argument(
                "command",
                choices=["check", "setup", "env", "deploy", "trigger", "status", "destroy", "import"],
            )
            parsed = args.parse_args(["--env", "prod", cmd])
            assert parsed.command == cmd
            assert parsed.env == "prod"

    def test_invalid_command_rejected(self):
        parser = dokploy.argparse.ArgumentParser()
        parser.add_argument("--env", default=None)
        parser.add_argument(
            "command",
            choices=["check", "setup", "env", "deploy", "trigger", "status", "destroy", "import"],
        )
        with pytest.raises(SystemExit):
            parser.parse_args(["bogus"])

    def test_env_flag_parsed(self):
        parser = dokploy.argparse.ArgumentParser()
        parser.add_argument("--env", default=None)
        parser.add_argument(
            "command",
            choices=["check", "setup", "env", "deploy", "trigger", "status", "destroy", "import"],
        )
        parsed = parser.parse_args(["--env", "staging", "deploy"])
        assert parsed.env == "staging"
        assert parsed.command == "deploy"


class TestGetStateFile:
    def test_returns_correct_path(self, tmp_path):
        result = dokploy.get_state_file(tmp_path, "prod")
        assert result == tmp_path / ".dokploy-state" / "prod.json"


class TestBuildGithubProviderPayload:
    def test_defaults(self):
        """Minimal app_def produces default buildPath, triggerType, watchPaths."""
        result = dokploy.build_github_provider_payload(
            "app-1",
            {"name": "web", "source": "github"},
            {"owner": "org", "repository": "repo", "branch": "main"},
            "gh-123",
        )
        assert result == {
            "applicationId": "app-1",
            "repository": "repo",
            "branch": "main",
            "owner": "org",
            "buildPath": "/",
            "githubId": "gh-123",
            "enableSubmodules": False,
            "triggerType": "push",
            "watchPaths": None,
        }

    def test_custom_values(self):
        """Per-app overrides for buildPath, triggerType, watchPaths are passed through."""
        app_def = {
            "name": "web",
            "source": "github",
            "buildPath": "/app",
            "triggerType": "manual",
            "watchPaths": ["src/**", "Dockerfile"],
        }
        result = dokploy.build_github_provider_payload(
            "app-1",
            app_def,
            {"owner": "org", "repository": "repo", "branch": "main"},
            "gh-123",
        )
        assert result["buildPath"] == "/app"
        assert result["triggerType"] == "manual"
        assert result["watchPaths"] == ["src/**", "Dockerfile"]


class TestBuildBuildTypePayload:
    def test_default_dockerfile(self):
        """No buildType defaults to dockerfile with Dockerfile defaults."""
        result = dokploy.build_build_type_payload("app-1", {"name": "web"})
        assert result == {
            "applicationId": "app-1",
            "buildType": "dockerfile",
            "dockerfile": "Dockerfile",
            "dockerContextPath": "",
            "dockerBuildStage": "",
            "herokuVersion": None,
            "railpackVersion": None,
        }

    def test_explicit_dockerfile(self):
        """Explicit dockerfile settings are passed through."""
        app_def = {
            "name": "web",
            "buildType": "dockerfile",
            "dockerfile": "docker/Dockerfile.prod",
            "dockerContextPath": ".",
            "dockerBuildStage": "production",
        }
        result = dokploy.build_build_type_payload("app-1", app_def)
        assert result["dockerfile"] == "docker/Dockerfile.prod"
        assert result["dockerContextPath"] == "."
        assert result["dockerBuildStage"] == "production"

    def test_static_build_type(self):
        """Static buildType includes publishDirectory, SPA flag, and required API fields."""
        app_def = {
            "name": "site",
            "buildType": "static",
            "publishDirectory": "dist",
        }
        result = dokploy.build_build_type_payload("app-1", app_def)
        assert result == {
            "applicationId": "app-1",
            "buildType": "static",
            "publishDirectory": "dist",
            "isStaticSpa": False,
            "dockerContextPath": "",
            "dockerBuildStage": "",
            "herokuVersion": None,
            "railpackVersion": None,
        }
        assert "dockerfile" not in result

    def test_static_default_publish_directory(self):
        """Static buildType without publishDirectory defaults to empty string."""
        result = dokploy.build_build_type_payload("app-1", {"name": "site", "buildType": "static"})
        assert result["publishDirectory"] == ""

    def test_nixpacks_build_type(self):
        """Nixpacks buildType includes required API fields only."""
        result = dokploy.build_build_type_payload("app-1", {"name": "app", "buildType": "nixpacks"})
        assert result == {
            "applicationId": "app-1",
            "buildType": "nixpacks",
            "dockerContextPath": "",
            "dockerBuildStage": "",
            "herokuVersion": None,
            "railpackVersion": None,
        }

    def test_all_build_types_include_required_api_fields(self):
        """Dokploy API requires dockerContextPath, dockerBuildStage, herokuVersion, railpackVersion for all build types."""
        for build_type in ("dockerfile", "static", "nixpacks", "heroku_buildpacks"):
            result = dokploy.build_build_type_payload("app-1", {"name": "x", "buildType": build_type})
            assert "dockerContextPath" in result, f"missing dockerContextPath for {build_type}"
            assert "dockerBuildStage" in result, f"missing dockerBuildStage for {build_type}"
            assert "herokuVersion" in result, f"missing herokuVersion for {build_type}"
            assert "railpackVersion" in result, f"missing railpackVersion for {build_type}"

    def test_static_spa_included_when_true(self):
        """Static build with SPA=true passes isStaticSpa to the API."""
        app_def = {
            "name": "site",
            "buildType": "static",
            "publishDirectory": "dist",
            "isStaticSpa": True,
        }
        result = dokploy.build_build_type_payload("app-1", app_def)
        assert result["isStaticSpa"] is True

    def test_static_spa_defaults_false(self):
        """Static build without explicit SPA defaults to false."""
        app_def = {"name": "site", "buildType": "static"}
        result = dokploy.build_build_type_payload("app-1", app_def)
        assert result.get("isStaticSpa") is False


class TestBuildDomainPayload:
    def test_required_fields_only(self):
        """Minimal domain with only required fields."""
        dom = {
            "host": "example.com",
            "port": 8080,
            "https": True,
            "certificateType": "letsencrypt",
        }
        result = dokploy.build_domain_payload("app-1", dom)
        assert result == {
            "applicationId": "app-1",
            "host": "example.com",
            "port": 8080,
            "https": True,
            "certificateType": "letsencrypt",
        }
        assert "path" not in result
        assert "internalPath" not in result
        assert "stripPath" not in result

    def test_with_path(self):
        """Domain with path field is included in payload."""
        dom = {
            "host": "example.com",
            "port": 80,
            "https": True,
            "certificateType": "letsencrypt",
            "path": "/docs",
        }
        result = dokploy.build_domain_payload("app-1", dom)
        assert result["path"] == "/docs"

    def test_all_optional_fields(self):
        """All optional domain fields (path, internalPath, stripPath) included."""
        dom = {
            "host": "example.com",
            "port": 80,
            "https": True,
            "certificateType": "letsencrypt",
            "path": "/api",
            "internalPath": "/v2",
            "stripPath": True,
        }
        result = dokploy.build_domain_payload("app-1", dom)
        assert result["path"] == "/api"
        assert result["internalPath"] == "/v2"
        assert result["stripPath"] is True


class TestBuildAppSettingsPayload:
    def test_no_settings_returns_none(self):
        """App with no autoDeploy/replicas returns None."""
        result = dokploy.build_app_settings_payload("app-1", {"name": "web"})
        assert result is None

    def test_auto_deploy_only(self):
        """Only autoDeploy set."""
        result = dokploy.build_app_settings_payload("app-1", {"name": "web", "autoDeploy": True})
        assert result == {"applicationId": "app-1", "autoDeploy": True}

    def test_replicas_only(self):
        """Only replicas set."""
        result = dokploy.build_app_settings_payload("app-1", {"name": "web", "replicas": 3})
        assert result == {"applicationId": "app-1", "replicas": 3}

    def test_both_settings(self):
        """Both autoDeploy and replicas set."""
        result = dokploy.build_app_settings_payload("app-1", {"name": "web", "autoDeploy": False, "replicas": 2})
        assert result == {
            "applicationId": "app-1",
            "autoDeploy": False,
            "replicas": 2,
        }

    def test_auto_deploy_false_is_included(self):
        """autoDeploy=False is explicitly included (not treated as falsy)."""
        result = dokploy.build_app_settings_payload("app-1", {"name": "web", "autoDeploy": False})
        assert result is not None
        assert result["autoDeploy"] is False


class TestMergeEnvOverridesNewFields:
    def test_build_type_override_merges(self, github_static_config):
        """Environment override for autoDeploy/replicas merges into app."""
        merged = dokploy.merge_env_overrides(github_static_config, "prod")
        app = next(a for a in merged["apps"] if a["name"] == "app")
        # Base has autoDeploy=False, prod override has autoDeploy=True
        assert app["autoDeploy"] is True
        # Base has replicas=1, prod override has replicas=2
        assert app["replicas"] == 2

    def test_domain_override_merges(self, github_static_config):
        """Environment domain override merges into app."""
        expected = github_static_config["environments"]["prod"]["apps"]["app"]["domain"]
        merged = dokploy.merge_env_overrides(github_static_config, "prod")
        app = next(a for a in merged["apps"] if a["name"] == "app")
        assert app["domain"]["host"] == expected["host"]
        assert app["domain"]["port"] == expected["port"]
        assert app["domain"]["https"] == expected["https"]
        assert "path" not in app["domain"]

    def test_base_build_type_preserved(self, github_static_config):
        """buildType from base config is preserved when not overridden."""
        merged = dokploy.merge_env_overrides(github_static_config, "prod")
        app = next(a for a in merged["apps"] if a["name"] == "app")
        assert app["buildType"] == "static"

    def test_watch_paths_in_config(self, github_dockerfile_config):
        """watchPaths from base config are preserved through merge."""
        merged = dokploy.merge_env_overrides(github_dockerfile_config, "prod")
        app = next(a for a in merged["apps"] if a["name"] == "app")
        assert app["watchPaths"] == [
            "config/**",
            "assets/**",
            "Dockerfile",
            "^(?!.*\\.md$).*$",
        ]


class TestValidateConfigNewFixtures:
    def test_static_config_valid(self, github_static_config):
        dokploy.validate_config(github_static_config)

    def test_dockerfile_config_valid(self, github_dockerfile_config):
        dokploy.validate_config(github_dockerfile_config)


class TestUnifiedDeploy:
    def test_trigger_command_accepted(self):
        """'trigger' is a valid CLI choice."""
        parser = dokploy.argparse.ArgumentParser()
        parser.add_argument("--env", default=None)
        parser.add_argument(
            "command",
            choices=["check", "setup", "env", "deploy", "trigger", "status", "destroy", "import"],
        )
        parsed = parser.parse_args(["trigger"])
        assert parsed.command == "trigger"

    def test_deploy_still_valid_command(self):
        """'deploy' remains a valid CLI choice."""
        parser = dokploy.argparse.ArgumentParser()
        parser.add_argument("--env", default=None)
        parser.add_argument(
            "command",
            choices=["check", "setup", "env", "deploy", "trigger", "status", "destroy", "import"],
        )
        parsed = parser.parse_args(["deploy"])
        assert parsed.command == "deploy"

    def test_cmd_trigger_exists(self):
        """dokploy.cmd_trigger is callable."""
        assert callable(dokploy.cmd_trigger)

    def test_fresh_project_runs_all_phases(self, tmp_path, monkeypatch):
        """Fresh project (no state file) runs check, setup, env, trigger in order."""
        calls = []
        state_file = tmp_path / ".dokploy-state" / "prod.json"

        monkeypatch.setattr(dokploy, "cmd_check", lambda repo_root: calls.append("check"))
        monkeypatch.setattr(dokploy, "cmd_setup", lambda client, cfg, sf: calls.append("setup"))
        monkeypatch.setattr(dokploy, "cmd_env", lambda client, cfg, sf, repo_root: calls.append("env"))
        monkeypatch.setattr(dokploy, "cmd_trigger", lambda client, cfg, sf: calls.append("trigger"))

        dokploy.cmd_deploy(
            repo_root=tmp_path,
            client="fake-client",
            cfg={"project": {}},
            state_file=state_file,
        )

        assert calls == ["check", "setup", "env", "trigger"]

    def test_existing_project_skips_setup(self, tmp_path, monkeypatch):
        """Existing project (state file present) skips setup."""
        calls = []
        state_file = tmp_path / ".dokploy-state" / "prod.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text("{}")

        monkeypatch.setattr(dokploy, "cmd_check", lambda repo_root: calls.append("check"))
        monkeypatch.setattr(dokploy, "cmd_setup", lambda client, cfg, sf: calls.append("setup"))
        monkeypatch.setattr(dokploy, "cmd_env", lambda client, cfg, sf, repo_root: calls.append("env"))
        monkeypatch.setattr(dokploy, "cmd_trigger", lambda client, cfg, sf: calls.append("trigger"))

        dokploy.cmd_deploy(
            repo_root=tmp_path,
            client="fake-client",
            cfg={"project": {}},
            state_file=state_file,
        )

        assert "setup" not in calls
        assert calls == ["check", "env", "trigger"]

    def test_phase_headers_printed(self, tmp_path, monkeypatch, capsys):
        """Each phase prints a header like '==> Phase N/4: ...'."""
        state_file = tmp_path / ".dokploy-state" / "prod.json"

        monkeypatch.setattr(dokploy, "cmd_check", lambda repo_root: None)
        monkeypatch.setattr(dokploy, "cmd_setup", lambda client, cfg, sf: None)
        monkeypatch.setattr(dokploy, "cmd_env", lambda client, cfg, sf, repo_root: None)
        monkeypatch.setattr(dokploy, "cmd_trigger", lambda client, cfg, sf: None)

        dokploy.cmd_deploy(
            repo_root=tmp_path,
            client="fake-client",
            cfg={"project": {}},
            state_file=state_file,
        )

        output = capsys.readouterr().out
        assert "==> Phase 1/4: check" in output
        assert "==> Phase 2/4: setup" in output
        assert "==> Phase 3/4: env" in output
        assert "==> Phase 4/4: trigger" in output

    def test_check_failure_stops_execution(self, tmp_path, monkeypatch):
        """If cmd_check raises SystemExit, subsequent phases are not called."""
        calls = []
        state_file = tmp_path / ".dokploy-state" / "prod.json"

        def failing_check(repo_root):
            calls.append("check")
            raise SystemExit(1)

        monkeypatch.setattr(dokploy, "cmd_check", failing_check)
        monkeypatch.setattr(dokploy, "cmd_setup", lambda client, cfg, sf: calls.append("setup"))
        monkeypatch.setattr(dokploy, "cmd_env", lambda client, cfg, sf, repo_root: calls.append("env"))
        monkeypatch.setattr(dokploy, "cmd_trigger", lambda client, cfg, sf: calls.append("trigger"))

        with pytest.raises(SystemExit):
            dokploy.cmd_deploy(
                repo_root=tmp_path,
                client="fake-client",
                cfg={"project": {}},
                state_file=state_file,
            )

        assert calls == ["check"]


def _state_with_app(app_name="web", app_id="app-123", dokploy_name="app-foo-bar-abc"):
    return {
        "projectId": "proj-1",
        "environmentId": "env-1",
        "apps": {
            app_name: {
                "applicationId": app_id,
                "appName": dokploy_name,
            }
        },
    }


CONTAINERS_RESPONSE = [
    {"containerId": "abc123running", "name": "app-foo-bar-abc.1.task1", "state": "running"},
    {"containerId": "def456exited1", "name": "app-foo-bar-abc.1.task2", "state": "exited"},
    {"containerId": "ghi789exited2", "name": "app-foo-bar-abc.1.task3", "state": "exited"},
]


class TestGetContainers:
    def test_returns_containers_from_api(self):
        client = MagicMock()
        client.get.return_value = CONTAINERS_RESPONSE
        result = dokploy.get_containers(client, "app-foo-bar-abc")
        client.get.assert_called_once_with(
            "docker.getContainersByAppNameMatch",
            params={"appName": "app-foo-bar-abc"},
        )
        assert len(result) == 3

    def test_empty_containers(self):
        client = MagicMock()
        client.get.return_value = []
        result = dokploy.get_containers(client, "app-no-exist")
        assert result == []


class TestSelectContainer:
    def test_default_selects_first(self):
        container = dokploy.select_container(CONTAINERS_RESPONSE, exited=False)
        assert container["containerId"] == "abc123running"

    def test_default_selects_first_even_if_exited(self):
        exited_only = [c for c in CONTAINERS_RESPONSE if c["state"] == "exited"]
        container = dokploy.select_container(exited_only, exited=False)
        assert container["containerId"] == "def456exited1"

    def test_for_exec_requires_running(self, capsys):
        exited_only = [c for c in CONTAINERS_RESPONSE if c["state"] == "exited"]
        with pytest.raises(SystemExit):
            dokploy.select_container(exited_only, exited=False, for_exec=True)
        assert "No running container" in capsys.readouterr().out

    def test_for_exec_selects_running(self):
        container = dokploy.select_container(CONTAINERS_RESPONSE, exited=False, for_exec=True)
        assert container["containerId"] == "abc123running"
        assert container["state"] == "running"

    def test_exited_flag_prompts_selection(self):
        with patch("builtins.input", return_value="1"):
            container = dokploy.select_container(CONTAINERS_RESPONSE, exited=True)
        assert container["containerId"] == "abc123running"

    def test_exited_selection_by_index(self):
        with patch("builtins.input", return_value="2"):
            container = dokploy.select_container(CONTAINERS_RESPONSE, exited=True)
        assert container["containerId"] == "def456exited1"

    def test_exited_invalid_input_retries(self, capsys):
        with patch("builtins.input", side_effect=["0", "999", "abc", "2"]):
            container = dokploy.select_container(CONTAINERS_RESPONSE, exited=True)
        assert container["containerId"] == "def456exited1"

    def test_empty_containers_exits(self, capsys):
        with pytest.raises(SystemExit):
            dokploy.select_container([], exited=False)
        assert "No containers found" in capsys.readouterr().out


class TestBuildDockerUrl:
    def test_default_port(self):
        ssh_cfg = {"host": "dokploy.example.com", "user": "root", "port": 22}
        url = dokploy.build_docker_url(ssh_cfg)
        assert url == "ssh://root@dokploy.example.com"

    def test_custom_port(self):
        ssh_cfg = {"host": "dokploy.example.com", "user": "deploy", "port": 2222}
        url = dokploy.build_docker_url(ssh_cfg)
        assert url == "ssh://deploy@dokploy.example.com:2222"

    def test_default_user(self):
        ssh_cfg = {"host": "10.0.0.1"}
        url = dokploy.build_docker_url(ssh_cfg)
        assert url == "ssh://root@10.0.0.1"


class TestGetDockerClient:
    def test_creates_client_with_ssh_url(self):
        ssh_cfg = {"host": "dokploy.example.com", "user": "ubuntu", "port": 22}
        with patch.object(dokploy.docker, "DockerClient") as mock_cls:
            dokploy.get_docker_client(ssh_cfg)
            mock_cls.assert_called_once_with(
                base_url="ssh://ubuntu@dokploy.example.com",
                use_ssh_client=True,
            )


class TestGetSshConfig:
    def test_reads_from_env(self):
        env = {
            "DOKPLOY_SSH_HOST": "myhost.com",
            "DOKPLOY_SSH_USER": "deploy",
            "DOKPLOY_SSH_PORT": "2222",
        }
        with patch.object(
            dokploy,
            "config",
            side_effect=lambda k, **kw: env.get(k, kw.get("default", "")),
        ):
            cfg = dokploy.get_ssh_config()
        assert cfg == {"host": "myhost.com", "user": "deploy", "port": 2222}

    def test_defaults(self):
        env = {"DOKPLOY_SSH_HOST": "myhost.com"}

        def _config(k, **kw):
            return env.get(k, kw.get("default", ""))

        with patch.object(dokploy, "config", side_effect=_config):
            cfg = dokploy.get_ssh_config()
        assert cfg == {"host": "myhost.com", "user": "root", "port": 22}

    def test_missing_host_exits(self, capsys):
        with (
            patch.object(
                dokploy,
                "config",
                side_effect=lambda k, **kw: kw.get("default", ""),
            ),
            pytest.raises(SystemExit),
        ):
            dokploy.get_ssh_config()
        assert "DOKPLOY_SSH_HOST" in capsys.readouterr().out


class TestResolveAppForExec:
    def test_resolves_from_state(self):
        state = _state_with_app("web", "app-123", "app-foo-bar-abc")
        app_name = dokploy.resolve_app_for_exec(state, "web")
        assert app_name == "app-foo-bar-abc"

    def test_unknown_app_exits(self, capsys):
        state = _state_with_app("web", "app-123", "app-foo-bar-abc")
        with pytest.raises(SystemExit):
            dokploy.resolve_app_for_exec(state, "nonexistent")
        assert "Unknown app" in capsys.readouterr().out

    def test_single_app_auto_selects(self):
        state = _state_with_app("web", "app-123", "app-foo-bar-abc")
        app_name = dokploy.resolve_app_for_exec(state, None)
        assert app_name == "app-foo-bar-abc"

    def test_multiple_apps_no_name_exits(self, capsys):
        state = _state_with_app("web", "app-123", "app-foo-bar-abc")
        state["apps"]["worker"] = {
            "applicationId": "app-456",
            "appName": "app-baz-qux-def",
        }
        with pytest.raises(SystemExit):
            dokploy.resolve_app_for_exec(state, None)
        assert "specify an app" in capsys.readouterr().out
