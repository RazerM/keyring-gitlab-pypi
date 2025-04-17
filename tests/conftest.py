import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch, TempPathFactory

from keyrings.gitlab_pypi import GitlabPypi


@pytest.fixture(autouse=True)
def config_home(monkeypatch: MonkeyPatch, tmp_path_factory: TempPathFactory) -> Path:
    config_home = tmp_path_factory.mktemp("config")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    return config_home


TEST_CONFIG = """\
["https://gitlab-a.example.com"]
token = "a"

["https://gitlab-b.example.com/"]
token = "b"

["gitlab-c.example.com"]
token = "c"

["gitlab-d.example.com/"]
token = "d"
"""


@pytest.fixture
def config_file(config_home: Path) -> Path:
    path = config_home / "gitlab-pypi.toml"
    path.write_text(TEST_CONFIG)
    return path


@pytest.fixture(autouse=True)
def isolate_ci_env(monkeypatch: MonkeyPatch) -> None:
    keys = [
        key
        for key in os.environ.keys()
        if key.startswith("CI_") or key.startswith("GITLAB_")
    ]
    for key in keys:
        monkeypatch.delenv(key)


@pytest.fixture
def mock_ci(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_CI", "true")
    monkeypatch.setenv("CI_API_V4_URL", "https://gitlab.example.com/api/v4")
    monkeypatch.setenv("CI_JOB_TOKEN", "some-ci-job-token")


@pytest.fixture
def backend() -> GitlabPypi:
    return GitlabPypi()
