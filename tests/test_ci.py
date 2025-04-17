from __future__ import annotations

import os

from keyring.credentials import SimpleCredential
from yarl import URL

from keyrings.gitlab_pypi import GitlabPypi


def url(
    *, scheme: str = "https", host: str = "gitlab.example.com", port: int | None = None
) -> str:
    url = URL.build(scheme=scheme, host=host, port=port).with_path("/api/v4")
    return str(url.joinpath("projects/1/packages/pypi/simple/keyring-gitlab-pypi"))


def purl(
    *, scheme: str = "https", host: str = "gitlab.example.com", port: int | None = None
) -> str:
    url = URL.build(scheme=scheme, host=host, port=port).with_path("/api/v4")
    return str(
        url.joinpath(
            "projects/1/packages/pypi/files/"
            "fb87de1c45c34ab4557e88dd5fd0d4e12154b84f7427722d3349a6fda7954ec1/"
            "keyring-gitlab-pypi-1.0.0-py3-none-any.whl"
        )
    )


def test_get_password(backend: GitlabPypi, mock_ci: None) -> None:
    assert backend.get_password(url(), "gitlab-ci-token") == os.environ["CI_JOB_TOKEN"]
    assert backend.get_password(purl(), "gitlab-ci-token") == os.environ["CI_JOB_TOKEN"]


def test_get_credential(backend: GitlabPypi, mock_ci: None) -> None:
    credential = backend.get_credential(url(), None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == "gitlab-ci-token"
    assert credential.password == os.environ["CI_JOB_TOKEN"]
    credential = backend.get_credential(purl(), None)
    assert credential.username == "gitlab-ci-token"
    assert credential.password == os.environ["CI_JOB_TOKEN"]


def test_not_ci(backend: GitlabPypi) -> None:
    assert backend.get_password(url(), "gitlab-ci-token") is None
    assert backend.get_password(purl(), "gitlab-ci-token") is None
    assert backend.get_credential(url(), None) is None
    assert backend.get_credential(purl(), None) is None


def test_missing_ci_api_v4_url_env(backend: GitlabPypi, mock_ci: None) -> None:
    del os.environ["CI_API_V4_URL"]
    assert backend.get_password(url(), "gitlab-ci-token") is None
    assert backend.get_password(purl(), "gitlab-ci-token") is None
    assert backend.get_credential(url(), None) is None
    assert backend.get_credential(purl(), None) is None


def test_missing_ci_job_token(backend: GitlabPypi, mock_ci: None) -> None:
    del os.environ["CI_JOB_TOKEN"]
    assert backend.get_password(url(), "gitlab-ci-token") is None
    assert backend.get_password(purl(), "gitlab-ci-token") is None
    assert backend.get_credential(url(), None) is None
    assert backend.get_credential(purl(), None) is None


def test_wrong_scheme(backend: GitlabPypi, mock_ci: None) -> None:
    assert backend.get_password(url(scheme="http"), "gitlab-ci-token") is None
    assert backend.get_password(purl(scheme="http"), "gitlab-ci-token") is None
    assert backend.get_credential(url(scheme="http"), None) is None
    assert backend.get_credential(purl(scheme="http"), None) is None
    assert backend.get_password(url(), "gitlab-ci-token") is not None
    assert backend.get_password(purl(), "gitlab-ci-token") is not None
    assert backend.get_credential(url(), None) is not None
    assert backend.get_credential(purl(), None) is not None


def test_wrong_host(backend: GitlabPypi, mock_ci: None) -> None:
    assert backend.get_password(url(host="example.com"), "gitlab-ci-token") is None
    assert backend.get_password(purl(host="example.com"), "gitlab-ci-token") is None
    assert backend.get_credential(url(host="example.com"), None) is None
    assert backend.get_credential(purl(host="example.com"), None) is None
    assert backend.get_password(url(), "gitlab-ci-token") is not None
    assert backend.get_password(purl(), "gitlab-ci-token") is not None
    assert backend.get_credential(url(), None) is not None
    assert backend.get_credential(purl(), None) is not None


def test_wrong_port(backend: GitlabPypi, mock_ci: None) -> None:
    assert backend.get_password(url(port=8443), "gitlab-ci-token") is None
    assert backend.get_password(purl(port=8443), "gitlab-ci-token") is None
    assert backend.get_credential(url(port=8443), None) is None
    assert backend.get_credential(purl(port=8443), None) is None
    assert backend.get_password(url(), "gitlab-ci-token") is not None
    assert backend.get_password(purl(), "gitlab-ci-token") is not None
    assert backend.get_credential(url(), None) is not None
    assert backend.get_credential(purl(), None) is not None


def test_get_password_wrong_username(backend: GitlabPypi, mock_ci: None) -> None:
    assert backend.get_password(url(), "alice") is None
    assert backend.get_password(purl(), "bob") is None
    assert backend.get_password(url(), "gitlab-ci-token") is not None
    assert backend.get_password(purl(), "gitlab-ci-token") is not None
