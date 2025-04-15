from pathlib import Path

import pytest
from pytest import MonkeyPatch, TempPathFactory


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
