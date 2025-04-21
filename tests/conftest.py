import os
import re
import sys
from pathlib import Path

import pytest
from attrs import define, field
from platformdirs import user_config_path
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import Metafunc, MonkeyPatch

from keyrings.gitlab_pypi import GitlabPypi


@define
class ConfigDirEnv:
    path: Path
    env: dict[str, str] = field(factory=dict)


def pytest_generate_tests(metafunc: Metafunc) -> None:
    if "config_dir_env" in metafunc.fixturenames:
        home = Path.home()
        if sys.platform == "darwin":
            dirs = [
                ConfigDirEnv(home / "Library/Application Support/gitlab-pypi"),
                ConfigDirEnv(home / ".config"),
            ]
        elif sys.platform == "linux":
            config_home = home / ".customconfig"
            dirs = [
                ConfigDirEnv(home / ".config"),
                ConfigDirEnv(config_home, {"XDG_CONFIG_HOME": str(config_home)}),
            ]
        else:
            dirs = [ConfigDirEnv(user_config_path("gitlab-pypi", appauthor=False))]
        metafunc.parametrize("config_dir_env", dirs)


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
def config_file(
    config_dir_env: ConfigDirEnv, monkeypatch: MonkeyPatch, fs: FakeFilesystem
) -> Path:
    config_dir_env.path.mkdir(parents=True)
    for key, value in config_dir_env.env.items():
        monkeypatch.setenv(key, value)
    path = config_dir_env.path / "gitlab-pypi.toml"
    path.write_text(TEST_CONFIG)
    return path


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: MonkeyPatch) -> None:
    keys = [key for key in os.environ.keys() if re.match(r"(CI|GITLAB|XDG)_", key)]
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
