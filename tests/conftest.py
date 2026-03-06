"""Shared fixtures for dokploy unit tests."""

import pytest
import yaml


@pytest.fixture
def web_app_config():
    """Realistic config based on examples/web-app/dokploy.yml."""
    return {
        "project": {
            "name": "my-web-app",
            "description": "Web application with async task processing\n",
            "env_targets": ["web", "worker", "beat"],
            "deploy_order": [["redis"], ["web", "worker", "beat", "flower"]],
        },
        "github": {
            "owner": "your-org",
            "repository": "your-app",
            "branch": "main",
        },
        "environments": {
            "prod": {
                "apps": {
                    "web": {
                        "domain": {
                            "host": "app.example.com",
                            "port": 8000,
                            "https": True,
                            "certificateType": "letsencrypt",
                        }
                    },
                    "flower": {
                        "domain": {
                            "host": "flower.example.com",
                            "port": 5555,
                            "https": True,
                            "certificateType": "letsencrypt",
                        }
                    },
                },
            },
            "dev": {
                "github": {"branch": "develop"},
                "apps": {
                    "web": {
                        "domain": {
                            "host": "app-dev.example.com",
                            "port": 8000,
                            "https": True,
                            "certificateType": "letsencrypt",
                        }
                    },
                },
            },
        },
        "apps": [
            {"name": "redis", "source": "docker", "dockerImage": "redis:7-alpine"},
            {"name": "web", "source": "github"},
            {
                "name": "worker",
                "source": "github",
                "command": "celery -A myproject worker --loglevel=INFO",
            },
            {
                "name": "beat",
                "source": "github",
                "command": "celery -A myproject beat --loglevel=INFO",
            },
            {
                "name": "flower",
                "source": "docker",
                "dockerImage": "mher/flower:2.0.1",
                "command": "celery --broker=redis://{redis}:6379/0 flower --port=5555",
                "env": "CELERY_BROKER_URL=redis://{redis}:6379/0\n",
            },
        ],
    }


@pytest.fixture
def minimal_config():
    """Minimal valid config based on examples/minimal/dokploy.yml."""
    return {
        "project": {
            "name": "my-app",
            "description": "Single container deployment\n",
            "deploy_order": [["app"]],
        },
        "environments": {
            "prod": {
                "apps": {
                    "app": {
                        "domain": {
                            "host": "app.example.com",
                            "port": 3000,
                            "https": True,
                            "certificateType": "letsencrypt",
                        }
                    }
                }
            }
        },
        "apps": [
            {"name": "app", "source": "docker", "dockerImage": "nginx:alpine"},
        ],
    }


@pytest.fixture
def docker_only_config():
    """Docker-only config based on examples/docker-only/dokploy.yml."""
    return {
        "project": {
            "name": "my-docker-stack",
            "description": "Docker-only deployment\n",
            "deploy_order": [["postgres", "redis"], ["app"]],
        },
        "environments": {
            "prod": {
                "apps": {
                    "app": {
                        "domain": {
                            "host": "app.example.com",
                            "port": 3000,
                            "https": True,
                            "certificateType": "letsencrypt",
                        }
                    }
                }
            }
        },
        "apps": [
            {
                "name": "postgres",
                "source": "docker",
                "dockerImage": "postgres:17-alpine",
            },
            {"name": "redis", "source": "docker", "dockerImage": "redis:7-alpine"},
            {
                "name": "app",
                "source": "docker",
                "dockerImage": "ghcr.io/your-org/your-app:latest",
                "env": "DATABASE_URL=postgresql://myapp:changeme@{postgres}:5432/myapp\n"
                "REDIS_URL=redis://{redis}:6379/0\n",
            },
        ],
    }


@pytest.fixture
def sample_state():
    """Sample state dict as saved by cmd_setup."""
    return {
        "projectId": "proj-abc123",
        "environmentId": "env-xyz789",
        "apps": {
            "redis": {
                "applicationId": "app-redis-001",
                "appName": "redis-abc123",
            },
            "web": {
                "applicationId": "app-web-002",
                "appName": "web-def456",
            },
            "worker": {
                "applicationId": "app-worker-003",
                "appName": "worker-ghi789",
            },
        },
    }


@pytest.fixture
def dokploy_yml(tmp_path, minimal_config):
    """Write a minimal dokploy.yml in tmp_path and return the path."""
    config_file = tmp_path / "dokploy.yml"
    config_file.write_text(yaml.dump(minimal_config))
    return config_file
