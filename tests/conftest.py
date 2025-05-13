from __future__ import annotations

import os
import re
import secrets
import string
import sys
from collections.abc import Mapping
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest
import tomli_w
from attrs import define, field
from platformdirs import user_config_path
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import FixtureRequest, Metafunc, MonkeyPatch
from yarl import URL

from keyrings.gitlab_pypi import GitlabPypi, iter_config_paths


def _convert_path_to_str(path: str | os.PathLike[str]) -> str:
    """Fix mypy for attrs converter arg."""
    return os.fspath(path)


def _convert_mapping_proxy(d: Mapping[str, str]) -> MappingProxyType[str, str]:
    """Fix mypy for attrs converter arg."""
    return MappingProxyType(d)


@define(frozen=True)
class ConfigDirEnv:
    # Prior to Python 3.11, we can't use Path objects created by
    # pytest_generate_tests because pyfakefs is not yet active. Instead, we
    # hold onto a str and lazily create a path when the property is accessed
    # in a test fixture.
    # https://pytest-pyfakefs.readthedocs.io/en/latest/troubleshooting.html#pathlib-path-objects-created-outside-of-tests
    _path: str = field(converter=_convert_path_to_str)
    env: Mapping[str, str] = field(factory=dict, converter=_convert_mapping_proxy)

    @cached_property
    def path(self) -> Path:
        return Path(self._path)


def pytest_generate_tests(metafunc: Metafunc) -> None:
    if "config_dir_env" in metafunc.fixturenames:
        home = Path.home()
        if sys.platform == "darwin":
            dirs = [
                ConfigDirEnv(home / "Library/Application Support/gitlab-pypi"),
                ConfigDirEnv(home / ".config"),
                ConfigDirEnv("/Library/Application Support/gitlab-pypi"),
            ]
            ids = ["macos-user", "macos-user-linux-like", "macos-system"]
        elif sys.platform == "linux":
            config_home = home / ".customconfig"
            dirs = [
                ConfigDirEnv(home / ".config"),
                ConfigDirEnv(config_home, {"XDG_CONFIG_HOME": str(config_home)}),
                ConfigDirEnv("/etc/xdg/gitlab-pypi"),
                ConfigDirEnv("/etc"),
                ConfigDirEnv("/etc/foo/gitlab-pypi", {"XDG_CONFIG_DIRS": "/etc/foo"}),
            ]
            ids = [
                "linux-user",
                "linux-user-xdg-config-home",
                "linux-system-xdg",
                "linux-system-etc",
                "linux-system-xdg-config-dirs",
            ]
        elif sys.platform == "win32":
            dirs = [
                ConfigDirEnv(home / "AppData/Local/gitlab-pypi"),
                ConfigDirEnv(r"C:\ProgramData\gitlab-pypi"),
            ]
            ids = [
                "windows-user",
                "windows-system",
            ]
        else:  # pragma: no cover
            dirs = [ConfigDirEnv(user_config_path("gitlab-pypi", appauthor=False))]
            ids = ["default-user"]
        metafunc.parametrize("config_dir_env", dirs, ids=ids)


@pytest.fixture(
    params=[
        "https://gitlab.example.com",
        "https://gitlab.example.com:8443",
        "http://gitlab.example.com",
        "http://gitlab.example.com:8080",
    ]
)
def gitlab_base_url(request: FixtureRequest) -> URL:
    return URL(request.param)


@pytest.fixture(
    params=[
        "simple/keyring-gitlab-pypi",
        f"files/{secrets.token_hex(32)}/foo-1.0.0-py3-none-any.whl",
    ],
    ids=["package", "file"],
)
def service(gitlab_base_url: URL, request: FixtureRequest) -> str:
    """Return a value for the `service` argument of the `get_password` /
    `get_credential` methods.
    """

    return str(
        gitlab_base_url.joinpath("api/v4/projects/1/packages/pypi", request.param)
    )


@pytest.fixture(
    params=[
        "simple/keyring-gitlab-pypi",
        f"files/{secrets.token_hex(32)}/foo-1.0.0-py3-none-any.whl",
    ],
    ids=["package", "file"],
)
def badservice(gitlab_base_url: URL, request: FixtureRequest) -> str:
    return str(
        gitlab_base_url.with_host("foo.example.com").joinpath(
            "api/v4/projects/1/packages/pypi", request.param
        )
    )


@pytest.fixture
def token() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(20))


@pytest.fixture(
    # s: explicit scheme even if https
    # p: explicit port even if default
    # t: trailing slash
    params=["", "s", "p", "t", "sp", "st", "pt", "spt"],
)
def section(request: FixtureRequest, gitlab_base_url: URL) -> str:
    urlspec = request.param
    url = gitlab_base_url
    parts = []
    assert re.match(r"^s?p?t?$", urlspec), "invalid urlspec"
    if "s" in urlspec or url.scheme != "https":
        parts.append(f"{url.scheme}://")

    assert url.host is not None
    parts.append(url.host)

    if "p" in urlspec or not url.is_default_port():
        parts.append(f":{url.port}")
    if "t" in urlspec:
        parts.append("/")
    return "".join(parts)


@pytest.fixture
def config_file(
    config_dir_env: ConfigDirEnv,
    monkeypatch: MonkeyPatch,
    fs: FakeFilesystem,
    token: str,
    section: str,
) -> Path:
    config_dir_env.path.mkdir(parents=True)
    for key, value in config_dir_env.env.items():
        monkeypatch.setenv(key, value)

    # Set bad tokens in lower precedence config files to verify that they are
    # not used.
    for lower_precedence_path in iter_config_paths():
        if lower_precedence_path == config_dir_env.path:
            break
        lower_precedence_path.mkdir(parents=True, exist_ok=True)
        doc = {section: {"token": f"token from {lower_precedence_path}"}}
        with open(lower_precedence_path / "gitlab-pypi.toml", "wb") as f:
            tomli_w.dump(doc, f)

    path = config_dir_env.path / "gitlab-pypi.toml"
    doc = {section: {"token": token}}
    with open(path, "wb") as f:
        tomli_w.dump(doc, f)
    return path


class InvalidConfig(Enum):
    NOT_A_TABLE = auto()
    NO_TOKEN = auto()
    BLANK_TOKEN = auto()
    NON_STR_TOKEN = auto()


@pytest.fixture(
    params=[
        InvalidConfig.NOT_A_TABLE,
        InvalidConfig.NO_TOKEN,
        InvalidConfig.BLANK_TOKEN,
        InvalidConfig.NON_STR_TOKEN,
    ]
)
def invalid_config_file(
    config_dir_env: ConfigDirEnv,
    monkeypatch: MonkeyPatch,
    fs: FakeFilesystem,
    token: str,
    section: str,
    request: FixtureRequest,
) -> Path:
    config_dir_env.path.mkdir(parents=True)
    for key, value in config_dir_env.env.items():
        monkeypatch.setenv(key, value)
    path = config_dir_env.path / "gitlab-pypi.toml"
    doc: Any
    if request.param is InvalidConfig.NOT_A_TABLE:
        doc = {section: ""}
    elif request.param is InvalidConfig.NO_TOKEN:
        doc = {section: {}}
    elif request.param is InvalidConfig.BLANK_TOKEN:
        doc = {section: {"token": ""}}
    elif request.param is InvalidConfig.NON_STR_TOKEN:
        doc = {section: {"token": 123}}
    else:
        raise NotImplementedError(request.param)

    with open(path, "wb") as f:
        tomli_w.dump(doc, f)
    return path


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: MonkeyPatch) -> None:
    keys = [key for key in os.environ.keys() if re.match(r"(CI|GITLAB|XDG)_", key)]
    for key in keys:
        monkeypatch.delenv(key)  # pragma: no cover


@pytest.fixture
def mock_ci(monkeypatch: MonkeyPatch, gitlab_base_url: URL) -> None:
    api_v4_url = gitlab_base_url.joinpath("api/v4")
    monkeypatch.setenv("GITLAB_CI", "true")
    monkeypatch.setenv("CI_API_V4_URL", str(api_v4_url))
    monkeypatch.setenv("CI_JOB_TOKEN", "some-ci-job-token")


@pytest.fixture
def backend() -> GitlabPypi:
    return GitlabPypi()
