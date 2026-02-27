from __future__ import annotations

import os
import random
import re
import secrets
import string
import sys
from collections.abc import Mapping
from enum import Enum, auto
from functools import cached_property, partial
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, cast
from typing import NoReturn as Never

import pytest
import tomli_w
from attrs import define, field, setters
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


@define
class Invalid:
    def unhandled(self, desc: str) -> Never:
        raise RuntimeError(
            f"{self!r} could not be used to set an invalid {desc}"
        )  # pragma: no cover


@define
class InvalidNotATable(Invalid):
    instance: str


@define
class InvalidValue(Invalid):
    value: Any


@define
class InvalidMissing(Invalid):
    pass


class Scenario(Protocol):
    monkeypatch: MonkeyPatch | None

    def configure(  # pragma: no cover
        self,
        instance: str | Invalid,
        username: str | None | Invalid,
        token: str | Invalid,
        *,
        create_lower_precedence_config_files: bool = True,
    ) -> None: ...


@define(on_setattr=setters.frozen)
class ConfigPathScenario(Scenario):
    """In this scenario, a config file should be created in the given path."""

    # Prior to Python 3.11, we can't use Path objects created by
    # pytest_generate_tests because pyfakefs is not yet active. Instead, we
    # hold onto a str and lazily create a path when the property is accessed
    # in a test fixture.
    # https://pytest-pyfakefs.readthedocs.io/en/latest/troubleshooting.html#pathlib-path-objects-created-outside-of-tests
    _path: str = field(converter=_convert_path_to_str)
    env: Mapping[str, str] = field(factory=dict, converter=_convert_mapping_proxy)
    monkeypatch: MonkeyPatch | None = field(
        init=False, default=None, on_setattr=setters.NO_OP
    )

    @cached_property
    def path(self) -> Path:
        return Path(self._path)

    def configure(
        self,
        instance: str | Invalid,
        username: str | None | Invalid,
        token: str | Invalid,
        *,
        create_lower_precedence_config_files: bool = True,
    ) -> None:
        assert self.monkeypatch is not None
        self.path.mkdir(parents=True)
        for key, value in self.env.items():
            self.monkeypatch.setenv(key, value)

        if (
            create_lower_precedence_config_files
            and not isinstance(instance, Invalid)
            and not isinstance(username, Invalid)
        ):
            _create_lower_precedence_config_files(instance, username, self.path)

        host_config = {}
        if isinstance(token, InvalidMissing):
            pass
        elif isinstance(token, InvalidValue):
            host_config["token"] = token.value
        elif isinstance(token, Invalid):
            token.unhandled("token")  # pragma: no cover
        else:
            host_config["token"] = token

        if isinstance(username, InvalidValue):
            host_config["username"] = username.value
        elif isinstance(username, Invalid):
            username.unhandled("username")  # pragma: no cover
        elif username is not None:
            host_config["username"] = username

        doc: dict[str, Any] = {}
        if isinstance(instance, InvalidNotATable):
            doc[instance.instance] = ""
        elif isinstance(instance, Invalid):
            instance.unhandled("instance")  # pragma: no cover
        else:
            doc[instance] = host_config
        with open(self.path / "gitlab-pypi.toml", "wb") as f:
            tomli_w.dump(doc, f)


@define(on_setattr=setters.frozen)
class EnvVarScenario(Scenario):
    """In this scenario, environment variables should be used for configuration."""

    monkeypatch: MonkeyPatch | None = field(
        init=False, default=None, on_setattr=setters.NO_OP
    )

    def configure(
        self,
        instance: str | Invalid,
        username: str | None | Invalid,
        token: str | Invalid,
        *,
        create_lower_precedence_config_files: bool = True,
    ) -> None:
        assert self.monkeypatch is not None
        if (
            create_lower_precedence_config_files
            and not isinstance(instance, Invalid)
            and not isinstance(username, Invalid)
        ):
            _create_lower_precedence_config_files(instance, username)

        key = "".join(random.choice(string.ascii_uppercase + "_") for _ in range(5))
        if isinstance(instance, InvalidNotATable):
            pytest.skip("not relevant for EnvVarScenario")
        elif isinstance(instance, Invalid):
            instance.unhandled("instance")  # pragma: no cover
        else:
            self.monkeypatch.setenv(f"KEYRING_GITLAB_PYPI_{key}_INSTANCE", instance)

        if isinstance(token, InvalidMissing):
            pass
        elif isinstance(token, InvalidValue):
            pytest.skip("not relevant for EnvVarScenario")
        elif isinstance(token, Invalid):
            token.unhandled("token")  # pragma: no cover
        else:
            self.monkeypatch.setenv(f"KEYRING_GITLAB_PYPI_{key}_TOKEN", token)

        if isinstance(username, InvalidValue):
            pytest.skip("not relevant for EnvVarScenario")
        elif isinstance(username, Invalid):
            username.unhandled("username")  # pragma: no cover
        elif username is not None:
            self.monkeypatch.setenv(f"KEYRING_GITLAB_PYPI_{key}_USERNAME", username)


def _create_lower_precedence_config_files(
    instance: str, username: str | None, path: Path | None = None
) -> None:
    assert path is None or path.is_dir() or not path.exists(), "expected directory"

    # Set bad tokens in lower precedence config files to verify that they are
    # not used.
    for lower_precedence_path in iter_config_paths():
        if path is not None and lower_precedence_path == path:
            break
        lower_precedence_path.mkdir(parents=True, exist_ok=True)
        host_config = {"token": f"token from {lower_precedence_path}"}
        if username is not None:
            host_config["username"] = username
        doc = {instance: host_config}

        with open(lower_precedence_path / "gitlab-pypi.toml", "wb") as f:
            tomli_w.dump(doc, f)


@pytest.fixture
def scenario(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
    fs: FakeFilesystem,
) -> Scenario:
    scenario = request.param
    scenario.monkeypatch = monkeypatch
    return cast(Scenario, scenario)


def pytest_generate_tests(metafunc: Metafunc) -> None:
    if "scenario" in metafunc.fixturenames:
        home = Path.home()
        if sys.platform == "darwin":
            dirs = [
                ConfigPathScenario(home / "Library/Application Support/gitlab-pypi"),
                ConfigPathScenario(home / ".config"),
                ConfigPathScenario("/Library/Application Support/gitlab-pypi"),
                EnvVarScenario(),
            ]
            ids = ["macos-user", "macos-user-linux-like", "macos-system", "env-vars"]
        elif sys.platform == "linux":
            config_home = home / ".customconfig"
            dirs = [
                ConfigPathScenario(home / ".config"),
                ConfigPathScenario(config_home, {"XDG_CONFIG_HOME": str(config_home)}),
                ConfigPathScenario("/etc/xdg/gitlab-pypi"),
                ConfigPathScenario("/etc"),
                ConfigPathScenario(
                    "/etc/foo/gitlab-pypi", {"XDG_CONFIG_DIRS": "/etc/foo"}
                ),
                EnvVarScenario(),
            ]
            ids = [
                "linux-user",
                "linux-user-xdg-config-home",
                "linux-system-xdg",
                "linux-system-etc",
                "linux-system-xdg-config-dirs",
                "env-vars",
            ]
        elif sys.platform == "win32":
            dirs = [
                ConfigPathScenario(home / "AppData/Local/gitlab-pypi"),
                ConfigPathScenario(r"C:\ProgramData\gitlab-pypi"),
                EnvVarScenario(),
            ]
            ids = ["windows-user", "windows-system", "env-vars"]
        else:  # pragma: no cover
            dirs = [
                ConfigPathScenario(user_config_path("gitlab-pypi", appauthor=False)),
                EnvVarScenario(),
            ]
            ids = ["default-user", "env-vars"]
        metafunc.parametrize("scenario", dirs, ids=ids, indirect=True)


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


@pytest.fixture
def deploy_token_username() -> str:
    return f"gitlab+deploy-token-{random.randint(0, 999):03d}"


@pytest.fixture(
    # s: explicit scheme even if https
    # p: explicit port even if default
    # t: trailing slash
    params=["", "s", "p", "t", "sp", "st", "pt", "spt"],
)
def instance(request: FixtureRequest, gitlab_base_url: URL) -> str:
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


@pytest.fixture(
    params=[None, "__token__"],
    ids=["implicit-username", "explicit-username"],
)
def config_file_access_token(
    scenario: Scenario,
    monkeypatch: MonkeyPatch,
    token: str,
    instance: str,
    request: FixtureRequest,
) -> None:
    scenario.configure(instance, request.param, token)


@pytest.fixture
def config_file_deploy_token(
    scenario: ConfigPathScenario,
    monkeypatch: MonkeyPatch,
    token: str,
    instance: str,
    deploy_token_username: str,
) -> None:
    scenario.configure(instance, deploy_token_username, token)


class InvalidConfig(Enum):
    NOT_A_TABLE = auto()
    NO_TOKEN = auto()
    BLANK_TOKEN = auto()
    NON_STR_TOKEN = auto()
    NON_STR_USERNAME = auto()


@pytest.fixture(
    params=[
        InvalidConfig.NOT_A_TABLE,
        InvalidConfig.NO_TOKEN,
        InvalidConfig.BLANK_TOKEN,
        InvalidConfig.NON_STR_TOKEN,
        InvalidConfig.NON_STR_USERNAME,
    ]
)
def invalid_config(
    scenario: Scenario,
    token: str,
    instance: str,
    request: FixtureRequest,
) -> None:
    configure = partial(scenario.configure, create_lower_precedence_config_files=False)
    if request.param is InvalidConfig.NOT_A_TABLE:
        configure(InvalidNotATable(instance), None, "")
    elif request.param is InvalidConfig.NO_TOKEN:
        configure(instance, None, InvalidMissing())
    elif request.param is InvalidConfig.BLANK_TOKEN:
        configure(instance, None, "")
    elif request.param is InvalidConfig.NON_STR_TOKEN:
        configure(instance, None, InvalidValue(123))
    elif request.param is InvalidConfig.NON_STR_USERNAME:
        configure(instance, InvalidValue(123), token)
    else:
        raise NotImplementedError(request.param)


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: MonkeyPatch) -> None:
    keys = [
        key
        for key in os.environ.keys()
        if re.match(r"(CI|GITLAB|XDG|KEYRING_GITLAB_PYPI)_", key)
    ]
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
