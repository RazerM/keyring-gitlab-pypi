from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING

import platformdirs
from keyring.backend import KeyringBackend
from keyring.credentials import SimpleCredential
from yarl import URL

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


CONFIG_APPNAME = "gitlab-pypi"
ENV_VAR_PATTERN = re.compile(
    r"^KEYRING_GITLAB_PYPI_(?P<name>.+)_(?P<field>INSTANCE|TOKEN|USERNAME)$"
)


def user_config_path() -> Path:
    if sys.platform == "darwin":
        # Use ~/Library/Application Support/gitlab-pypi if it exists
        path = platformdirs.user_config_path(CONFIG_APPNAME)
        if path.is_dir():
            return path

        # Default to Linux-like ~/.config
        return Path("~/.config").expanduser()

    if sys.platform == "linux":
        return platformdirs.user_config_path()

    return platformdirs.user_config_path(CONFIG_APPNAME, appauthor=False)


def system_config_paths() -> list[Path]:
    dirs = platformdirs.site_config_dir(
        CONFIG_APPNAME, appauthor=False, multipath=True
    ).split(os.pathsep)

    if sys.platform not in ("darwin", "win32"):
        dirs.append("/etc")

    return [Path(d) for d in dirs]


CONFIG_FILENAME = "gitlab-pypi.toml"


def _gitlab_url_from_service(service: str) -> URL | None:
    try:
        url = URL(service)
    except ValueError:
        return None

    if not re.match(r"^/api/v4/projects/[^/]+/packages/pypi", url.path):
        return None

    if url.scheme not in ("http", "https"):
        return None

    return url


def iter_config_paths() -> Iterator[Path]:
    """Yields config paths in order of lowest to highest precedence."""
    yield from system_config_paths()
    yield user_config_path()


def _load_access_credential(service: str) -> tuple[str, str] | None:
    url = _gitlab_url_from_service(service)

    if url is None:
        return None

    if credential := _load_access_credential_from_env(url):
        return credential

    # Since we don't need to merge config files, we can start with the
    # highest-precedence file and return the first token we find.
    for path in reversed(list(iter_config_paths())):
        if credential := _load_access_credential_from_config_path(path, url):
            return credential

    return None


def _load_access_credential_from_config_path(
    path: Path, url: URL
) -> tuple[str, str] | None:
    try:
        with open(path / CONFIG_FILENAME, "rb") as f:
            config = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None

    return _load_access_credential_from_config(config, url)


def _load_access_credential_from_env(url: URL) -> tuple[str, str] | None:
    groups: defaultdict[str, dict[str, str]] = defaultdict(dict)

    for key, value in os.environ.items():
        match = ENV_VAR_PATTERN.match(key)
        if match is None:
            continue

        name = match.group("name")
        field = match.group("field").lower()
        groups[name][field] = value

    config: dict[str, object] = {}
    for name in sorted(groups):
        group = groups[name]
        try:
            instance = group["instance"]
            token = group["token"]
        except KeyError:
            continue

        host_config: dict[str, str] = {"token": token}
        if "username" in group:
            host_config["username"] = group["username"]
        config[instance] = host_config

    return _load_access_credential_from_config(config, url)


def _load_access_credential_from_config(
    config: dict[str, object], url: URL
) -> tuple[str, str] | None:
    # Transform a URL like https://gitlab.com/api/v4/projects/0/packages/pypi/simple
    # into some keys that can be used:
    # - https://gitlab.com
    # - https://gitlab.com:443
    # - gitlab.com
    # - gitlab.com/

    prefixes = [f"{url.scheme}://"]
    if url.scheme == "https":
        prefixes.append("")

    assert url.port is not None
    portstrs = [f":{url.port}"]
    if url.is_default_port():
        portstrs.insert(0, "")

    suffixes = ["", "/"]

    keys = []
    for prefix, portstr, suffix in product(prefixes, portstrs, suffixes):
        keys.append(f"{prefix}{url.host}{portstr}{suffix}")

    for key in keys:
        try:
            host_config = config[key]
        except KeyError:
            continue

        if not isinstance(host_config, dict):
            continue

        try:
            token = host_config["token"]
        except KeyError:
            continue

        if not token:
            continue

        if not isinstance(token, str):
            continue

        username = host_config.get("username", "__token__")
        if not isinstance(username, str):
            continue

        return username, token

    return None


def _load_ci_job_token(service: str) -> str | None:
    url = _gitlab_url_from_service(service)

    if url is None:
        return None

    if not os.getenv("GITLAB_CI"):
        return None

    try:
        ci_api_url = URL(os.environ["CI_API_V4_URL"])
    except (KeyError, ValueError):
        return None

    if (
        url.scheme != ci_api_url.scheme
        or url.host != ci_api_url.host
        or url.port != ci_api_url.port
    ):
        return None

    token = os.getenv("CI_JOB_TOKEN")

    if not token:
        return None

    return token


class GitlabPypi(KeyringBackend):
    priority = 9

    if TYPE_CHECKING:

        def __init__(self) -> None: ...

    def get_password(self, service: str, username: str) -> str | None:
        if username == "gitlab-ci-token":
            return _load_ci_job_token(service)

        credential = _load_access_credential(service)
        if credential is None:
            return None

        config_username, token = credential
        if config_username == username:
            return token

        return None

    def set_password(self, service: str, username: str, password: str) -> None:
        raise NotImplementedError

    def delete_password(self, service: str, username: str) -> None:
        raise NotImplementedError

    def get_credential(
        self,
        service: str,
        username: str | None,
    ) -> SimpleCredential | None:
        if credential := _load_access_credential(service):
            return SimpleCredential(*credential)
        elif token := _load_ci_job_token(service):
            return SimpleCredential("gitlab-ci-token", token)

        return None
