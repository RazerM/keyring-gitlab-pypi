from __future__ import annotations

from pathlib import Path

import pytest
from keyring.credentials import SimpleCredential

from keyrings.gitlab_pypi import GitlabPypi


def url(subdomain: str) -> str:
    return f"https://{subdomain}.example.com/api/v4/projects/1/packages/pypi/simple/keyring-gitlab-pypi"


def purl(subdomain: str) -> str:
    return (
        f"https://{subdomain}.example.com/api/v4/projects/1/packages/pypi/files/"
        "fb87de1c45c34ab4557e88dd5fd0d4e12154b84f7427722d3349a6fda7954ec1/"
        "keyring-gitlab-pypi-1.0.0-py3-none-any.whl"
    )


@pytest.mark.parametrize(
    ("subdomain", "token"),
    [
        ("gitlab-a", "a"),
        ("gitlab-b", "b"),
        ("gitlab-c", "c"),
        ("gitlab-d", "d"),
    ],
)
def test_get_password(
    backend: GitlabPypi, config_file: Path, subdomain: str, token: str
) -> None:
    assert backend.get_password(url(subdomain), "__token__") == token
    assert backend.get_password(url(subdomain), "alice") is None
    assert backend.get_password(purl(subdomain), "__token__") == token
    assert backend.get_password(purl(subdomain), "bob") is None


@pytest.mark.parametrize(
    ("subdomain", "token"),
    [
        ("gitlab-a", "a"),
        ("gitlab-b", "b"),
        ("gitlab-c", "c"),
        ("gitlab-d", "d"),
    ],
)
@pytest.mark.parametrize("username", [None, "", "username", "__token__"])
def test_get_credential(
    backend: GitlabPypi,
    config_file: Path,
    subdomain: str,
    token: str,
    username: str | None,
) -> None:
    credential = backend.get_credential(url(subdomain), None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == "__token__"
    assert credential.password == token
    credential = backend.get_credential(purl(subdomain), None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == "__token__"
    assert credential.password == token


def test_get_password_unknown_url(backend: GitlabPypi, config_file: Path) -> None:
    assert backend.get_password(url("gitlab-e"), "__token__") is None


def test_get_password_no_config(backend: GitlabPypi) -> None:
    assert backend.get_password(url("gitlab-a"), "__token__") is None


def test_get_password_wrong_url(backend: GitlabPypi) -> None:
    assert backend.get_password("https://gitlab-a.example.com/foo", "__token__") is None


def test_get_credential_unknown_url(backend: GitlabPypi, config_file: Path) -> None:
    assert backend.get_credential(url("gitlab-e"), None) is None


def test_get_credential_no_config(backend: GitlabPypi) -> None:
    assert backend.get_credential(url("gitlab-a"), None) is None


def test_get_credential_wrong_url(backend: GitlabPypi) -> None:
    assert backend.get_credential("https://gitlab-a.example.com/foo", None) is None
