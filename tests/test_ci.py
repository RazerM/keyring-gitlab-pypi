from __future__ import annotations

import os

from keyring.credentials import SimpleCredential
from yarl import URL

from keyrings.gitlab_pypi import GitlabPypi


def test_get_password(backend: GitlabPypi, mock_ci: None, service: str) -> None:
    assert (
        backend.get_password(service, "gitlab-ci-token") == os.environ["CI_JOB_TOKEN"]
    )


def test_get_credential(backend: GitlabPypi, mock_ci: None, service: str) -> None:
    credential = backend.get_credential(service, None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == "gitlab-ci-token"
    assert credential.password == os.environ["CI_JOB_TOKEN"]


def test_not_ci(backend: GitlabPypi, service: str) -> None:
    assert backend.get_password(service, "gitlab-ci-token") is None
    assert backend.get_credential(service, None) is None


def test_missing_ci_api_v4_url_env(
    backend: GitlabPypi, mock_ci: None, service: str
) -> None:
    del os.environ["CI_API_V4_URL"]
    assert backend.get_password(service, "gitlab-ci-token") is None
    assert backend.get_credential(service, None) is None


def test_missing_ci_job_token(backend: GitlabPypi, mock_ci: None, service: str) -> None:
    del os.environ["CI_JOB_TOKEN"]
    assert backend.get_password(service, "gitlab-ci-token") is None
    assert backend.get_credential(service, None) is None


def test_wrong_scheme(backend: GitlabPypi, mock_ci: None, service: str) -> None:
    bad = str(URL(service).with_scheme("ftp"))
    assert backend.get_password(bad, "gitlab-ci-token") is None
    assert backend.get_credential(bad, None) is None
    assert backend.get_password(service, "gitlab-ci-token") is not None
    assert backend.get_credential(service, None) is not None


def test_wrong_host(backend: GitlabPypi, mock_ci: None, service: str) -> None:
    bad = str(URL(service).with_host("example.com"))
    assert backend.get_password(bad, "gitlab-ci-token") is None
    assert backend.get_credential(bad, None) is None
    assert backend.get_password(service, "gitlab-ci-token") is not None
    assert backend.get_credential(service, None) is not None


def test_wrong_port(backend: GitlabPypi, mock_ci: None, service: str) -> None:
    bad = str(URL(service).with_port(9999))
    assert backend.get_password(bad, "gitlab-ci-token") is None
    assert backend.get_credential(bad, None) is None
    assert backend.get_password(service, "gitlab-ci-token") is not None
    assert backend.get_credential(service, None) is not None


def test_get_password_wrong_username(
    backend: GitlabPypi, mock_ci: None, service: str
) -> None:
    assert backend.get_password(service, "alice") is None
    assert backend.get_password(service, "gitlab-ci-token") is not None
