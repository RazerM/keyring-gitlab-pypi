`keyring-gitlab-pypi` is a backend for [keyring] which recognises [GitLab package registry] URLs.

It is designed for use with [uv].

## How to use

1.  Install keyring with this backend

    ```bash
    uv tool install keyring --with keyring-gitlab-pypi
    ```

2.  Create a personal access token with `read_api` scope and add it to `~/.config/gitlab-pypi.toml`:

    ```toml
    ["https://gitlab.com"]
    token = "<token>"
    ```

3.  Configure [`keyring-provider`] in uv:

    - using an environment variable:

      ```bash
      export UV_KEYRING_PROVIDER=subprocess
      ```

    - or in `uv.toml`:

      ```toml
      keyring-provider = "subprocess"
      ```

    - or using the option

      ```bash
      uv sync --keyring-provider=subprocess
      ```

4.  Configure one or more GitLab package indexes

    For example, in `pyproject.toml`:

    ```toml
    [[tool.uv.index]]
    name = "myindex"
    url = "https://gitlab.example.com/api/v4/projects/1/packages/pypi/simple"
    authenticate = "always"
    ```

    **Note**

    You need `authenticate = "always"` for uv to invoke [keyring] when no
    username is specified. This option is a good idea anyway!

    Alternatively, add the username `__token__` to the URL, but this is not
    recommended for `pyproject.toml` as you likely want to use a different
    username in CI, for example.

5.  Done! `keyring-gitlab-pypi` will return your token for URLs that look like package installs.

## Motivation

- When using multiple GitLab package indexes, it can be cumbersome to configure them with the same token via environment variables or otherwise.
- [keyring]'s keychain backend on macOS does not support `--mode creds`
- uv will reuse credentials for URLs on the same host, but it feels fragile to just configure one of the indexes and let the credentials cache serve the rest. At the very least, `keyring-gitlab-pypi` is set-and-forget across multiple projects.

[keyring]: https://pypi.org/project/keyring/
[GitLab package registry]: https://docs.gitlab.com/user/packages/pypi_repository/#authenticate-with-the-gitlab-package-registry
[uv]: https://docs.astral.sh/uv/
[`keyring-provider`]: https://docs.astral.sh/uv/reference/settings/#keyring-provider
