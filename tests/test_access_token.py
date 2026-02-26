from __future__ import annotations

from pathlib import Path

import pytest
from keyring.credentials import SimpleCredential
from pyfakefs.fake_filesystem import FakeFilesystem
from yarl import URL

from keyrings.gitlab_pypi import GitlabPypi


def test_get_password(
    backend: GitlabPypi, config_file_access_token: Path, service: str, token: str
) -> None:
    assert backend.get_password(service, "__token__") == token


def test_get_password_wrong_username(
    backend: GitlabPypi, config_file_access_token: Path, service: str, token: str
) -> None:
    assert backend.get_password(service, "__token__") == token
    assert backend.get_password(service, "alice") is None


@pytest.mark.parametrize("username", [None, "", "username", "__token__"])
def test_get_credential(
    backend: GitlabPypi,
    config_file_access_token: Path,
    service: str,
    token: str,
    username: str | None,
) -> None:
    credential = backend.get_credential(service, None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == "__token__"
    assert credential.password == token


def test_get_password_unknown_url(
    backend: GitlabPypi, config_file_access_token: Path, badservice: str
) -> None:
    assert backend.get_password(badservice, "__token__") is None


def test_get_password_no_config(
    backend: GitlabPypi, fs: FakeFilesystem, service: str
) -> None:
    assert backend.get_password(service, "__token__") is None


def test_get_password_wrong_url(
    backend: GitlabPypi, config_file_access_token: Path, service: str
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
    backend: GitlabPypi, config_file_access_token: Path, badservice: str
) -> None:
    assert backend.get_credential(badservice, None) is None


def test_get_credential_no_config(
    backend: GitlabPypi, fs: FakeFilesystem, service: str
) -> None:
    assert backend.get_credential(service, None) is None


def test_get_credential_wrong_url(
    backend: GitlabPypi, config_file_access_token: Path, service: str
) -> None:
    service = service.replace("/pypi/", "/banana/")
    assert backend.get_credential(service, None) is None
