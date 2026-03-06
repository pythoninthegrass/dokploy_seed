"""Unit tests for pure functions in dokploy.py."""

import importlib.util
import json
import pytest
import sys
import yaml
from pathlib import Path

# Import dokploy.py as a module despite it being a PEP 723 script.
_SCRIPT = Path(__file__).resolve().parent.parent / "dokploy.py"
_spec = importlib.util.spec_from_file_location("dokploy", _SCRIPT)
dokploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dokploy)


# ---------------------------------------------------------------------------
# 1. find_repo_root
# ---------------------------------------------------------------------------
class TestFindRepoRoot:
    def test_finds_repo_root(self, tmp_path, monkeypatch):
        """find_repo_root walks up and returns the dir containing dokploy.yml."""
        (tmp_path / "dokploy.yml").write_text("project: {}")
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        # Make the function think the script lives in sub/
        monkeypatch.setattr(dokploy, "__file__", str(sub / "dokploy.py"))
        assert dokploy.find_repo_root() == tmp_path

    def test_exits_when_not_found(self, tmp_path, monkeypatch):
        """find_repo_root exits when no dokploy.yml is found."""
        monkeypatch.setattr(dokploy, "__file__", str(tmp_path / "dokploy.py"))
        with pytest.raises(SystemExit):
            dokploy.find_repo_root()


# ---------------------------------------------------------------------------
# 2. load_config
# ---------------------------------------------------------------------------
class TestLoadConfig:
    def test_loads_valid_yaml(self, tmp_path, minimal_config):
        cfg_file = tmp_path / "dokploy.yml"
        cfg_file.write_text(yaml.dump(minimal_config))
        result = dokploy.load_config(tmp_path)
        assert result["project"]["name"] == "my-app"

    def test_exits_on_missing_file(self, tmp_path):
        with pytest.raises(SystemExit):
            dokploy.load_config(tmp_path)


# ---------------------------------------------------------------------------
# 3. validate_config
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 4. validate_env_references
# ---------------------------------------------------------------------------
class TestValidateEnvReferences:
    def test_valid_refs_pass(self, web_app_config):
        dokploy.validate_env_references(web_app_config)

    def test_unknown_app_in_env_overrides_exits(self, minimal_config):
        minimal_config["environments"] = {
            "prod": {"apps": {"bogus": {"dockerImage": "x"}}}
        }
        with pytest.raises(SystemExit):
            dokploy.validate_env_references(minimal_config)

    def test_no_environments_passes(self, minimal_config):
        minimal_config.pop("environments", None)
        dokploy.validate_env_references(minimal_config)


# ---------------------------------------------------------------------------
# 5. merge_env_overrides
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 6. resolve_refs
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 7. get_env_exclude_prefixes
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 8. filter_env
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 9. load_state / save_state
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 10. main() argparse
# ---------------------------------------------------------------------------
class TestArgparse:
    def test_valid_commands(self):
        for cmd in ["check", "setup", "env", "deploy", "status", "destroy"]:
            args = dokploy.argparse.ArgumentParser()
            args.add_argument("--env", default=None)
            args.add_argument(
                "command",
                choices=["check", "setup", "env", "deploy", "status", "destroy"],
            )
            parsed = args.parse_args(["--env", "prod", cmd])
            assert parsed.command == cmd
            assert parsed.env == "prod"

    def test_invalid_command_rejected(self):
        parser = dokploy.argparse.ArgumentParser()
        parser.add_argument("--env", default=None)
        parser.add_argument(
            "command",
            choices=["check", "setup", "env", "deploy", "status", "destroy"],
        )
        with pytest.raises(SystemExit):
            parser.parse_args(["bogus"])

    def test_env_flag_parsed(self):
        parser = dokploy.argparse.ArgumentParser()
        parser.add_argument("--env", default=None)
        parser.add_argument(
            "command",
            choices=["check", "setup", "env", "deploy", "status", "destroy"],
        )
        parsed = parser.parse_args(["--env", "staging", "deploy"])
        assert parsed.env == "staging"
        assert parsed.command == "deploy"


# ---------------------------------------------------------------------------
# get_state_file (bonus — simple but worth a quick check)
# ---------------------------------------------------------------------------
class TestGetStateFile:
    def test_returns_correct_path(self, tmp_path):
        result = dokploy.get_state_file(tmp_path, "prod")
        assert result == tmp_path / ".dokploy-state" / "prod.json"
