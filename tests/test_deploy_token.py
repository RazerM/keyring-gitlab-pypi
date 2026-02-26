from __future__ import annotations

from keyring.credentials import SimpleCredential

from keyrings.gitlab_pypi import GitlabPypi


def test_get_password(
    backend: GitlabPypi,
    config_file_deploy_token: None,
    service: str,
    token: str,
    deploy_token_username: str,
) -> None:
    assert backend.get_password(service, "__token__") is None
    assert backend.get_password(service, deploy_token_username) == token


def test_get_credential(
    backend: GitlabPypi,
    config_file_deploy_token: None,
    service: str,
    token: str,
    deploy_token_username: str,
) -> None:
    credential = backend.get_credential(service, None)
    assert isinstance(credential, SimpleCredential)
    assert credential.username == deploy_token_username
    assert credential.password == token
