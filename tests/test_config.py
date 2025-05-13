from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from keyring.credentials import SimpleCredential
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import MonkeyPatch
from yarl import URL

from keyrings.gitlab_pypi import GitlabPypi, system_config_paths, user_config_path


def test_get_password(
    backend: GitlabPypi, config_file: Path, service: str, token: str
) -> None:
    assert backend.get_password(service, "__token__") == token


def test_get_password_wrong_username(
    backend: GitlabPypi, config_file: Path, service: str, token: str
) -> None:
    assert backend.get_password(service, "__token__") == token
    assert backend.get_password(service, "alice") is None


@pytest.mark.parametrize("username", [None, "", "username", "__token__"])
def test_get_credential(
    backend: GitlabPypi,
    config_file: Path,
    service: str,
    token: str,
    username: str | None,
) -> None:
    credential = backend.get_credential(service, None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == "__token__"
    assert credential.password == token


def test_get_password_unknown_url(
    backend: GitlabPypi, config_file: Path, badservice: str
) -> None:
    assert backend.get_password(badservice, "__token__") is None


def test_get_password_no_config(
    backend: GitlabPypi, fs: FakeFilesystem, service: str
) -> None:
    assert backend.get_password(service, "__token__") is None


def test_get_password_wrong_url(
    backend: GitlabPypi, config_file: Path, service: str
) -> None:
    service = service.replace("/pypi/", "/banana/")
    assert backend.get_password(service, "__token__") is None


def test_get_password_invalid_url(backend: GitlabPypi, fs: FakeFilesystem) -> None:
    assert backend.get_password("https://example.com:99999", "__token__") is None


def test_get_password_invalid_config(
    backend: GitlabPypi, invalid_config_file: Path, service: str
) -> None:
    assert backend.get_password(service, "__token__") is None


def test_get_password_invalid_url_scheme(
    backend: GitlabPypi, fs: FakeFilesystem, service: str
) -> None:
    service = str(URL(service).with_scheme("ftp"))
    assert backend.get_password(service, "__token__") is None


def test_get_credential_unknown_url(
    backend: GitlabPypi, config_file: Path, badservice: str
) -> None:
    assert backend.get_credential(badservice, None) is None


def test_get_credential_no_config(
    backend: GitlabPypi, fs: FakeFilesystem, service: str
) -> None:
    assert backend.get_credential(service, None) is None


def test_get_credential_wrong_url(
    backend: GitlabPypi, config_file: Path, service: str
) -> None:
    service = service.replace("/pypi/", "/banana/")
    assert backend.get_credential(service, None) is None


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux")
def test_linux_user_config_dir() -> None:
    assert user_config_path() == Path("~/.config").expanduser()


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS")
def test_macos_user_config_dir(fs: FakeFilesystem) -> None:
    # Default is Linux-like ~/.config
    assert user_config_path() == Path("~/.config").expanduser()

    # macOS convention will be used if it exists
    path = Path("~/Library/Application Support/gitlab-pypi").expanduser()
    fs.create_dir(path)
    assert user_config_path() == path


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows")
def test_windows_user_config_dir() -> None:
    localappdata = os.environ["LOCALAPPDATA"]
    assert user_config_path() == Path(localappdata, "gitlab-pypi")


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux")
def test_linux_system_config_dir(monkeypatch: MonkeyPatch) -> None:
    assert system_config_paths() == [Path("/etc/xdg/gitlab-pypi"), Path("/etc")]
    monkeypatch.setenv("XDG_CONFIG_DIRS", "/etc/foo:/etc/bar")
    assert system_config_paths() == [
        Path("/etc/foo/gitlab-pypi"),
        Path("/etc/bar/gitlab-pypi"),
        Path("/etc"),
    ]


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS")
def test_macos_system_config_dir() -> None:
    assert system_config_paths() == [Path("/Library/Application Support/gitlab-pypi")]


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows")
def test_windows_system_config_dir() -> None:
    allusersprofile = os.environ["ALLUSERSPROFILE"]
    assert system_config_paths() == [Path(allusersprofile, "gitlab-pypi")]
