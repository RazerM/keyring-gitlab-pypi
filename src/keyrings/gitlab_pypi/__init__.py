from __future__ import annotations

import os
import re
import sys
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


def user_config_path() -> Path:
    appname = "gitlab-pypi"
    if sys.platform == "darwin":
        # Use ~/Library/Application Support/gitlab-pypi if it exists
        path = platformdirs.user_config_path(appname)
        if path.is_dir():
            return path

        # Default to Linux-like ~/.config
        return Path("~/.config").expanduser()

    if sys.platform == "linux":
        return platformdirs.user_config_path()

    return platformdirs.user_config_path(appname, appauthor=False)


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


def _load_personal_access_token(service: str) -> str | None:
    url = _gitlab_url_from_service(service)

    if url is None:
        return None

    try:
        with open(user_config_path() / CONFIG_FILENAME, "rb") as f:
            config = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None

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

        if isinstance(token, str):
            return token

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
    priority = 9  # type: ignore[assignment]

    if TYPE_CHECKING:

        def __init__(self) -> None: ...

    def get_password(self, service: str, username: str) -> str | None:
        if username == "__token__":
            return _load_personal_access_token(service)
        elif username == "gitlab-ci-token":
            return _load_ci_job_token(service)

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
        if token := _load_personal_access_token(service):
            return SimpleCredential("__token__", token)
        elif token := _load_ci_job_token(service):
            return SimpleCredential("gitlab-ci-token", token)

        return None
