<p>
  <a href="https://pypi.org/project/keyring-gitlab-pypi/"><img src="https://img.shields.io/pypi/v/keyring-gitlab-pypi.svg" alt="PyPI" /></a>
  <a href="https://github.com/RazerM/keyring-gitlab-pypi/actions?workflow=CI"><img src="https://github.com/RazerM/keyring-gitlab-pypi/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI Status" /></a>
  <a href="https://codecov.io/github/RazerM/keyring-gitlab-pypi"><img src="https://codecov.io/github/RazerM/keyring-gitlab-pypi/graph/badge.svg?token=YFLPZEO0NB"/></a>
  <a href="https://raw.githubusercontent.com/RazerM/keyring-gitlab-pypi/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" /></a>
</p>

`keyring-gitlab-pypi` is a backend for [keyring] which recognises [GitLab package registry] URLs.

- ⚡️ Works seamlessly with [uv]
- 🚀 Zero config needed on GitLab CI
- 🗝️ No more per-index credentials on your machine

## Using it locally

1.  Install keyring with this backend

    ```bash
    uv tool install keyring --with keyring-gitlab-pypi
    ```

2.  Open the config file for editing:

    ### User

    <dl>
      <dt>macOS</dt>
      <dd><code>$HOME/Library/Application Support/gitlab-pypi/gitlab-pypi.toml</code> if directory <code>$HOME/Library/Application Support/gitlab-pypi</code> exists, or <code>$HOME/.config/gitlab-pypi.toml</code> otherwise.</dd>

      <dt>Linux</dt>
      <dd><code>$XDG_CONFIG_HOME/gitlab-pypi.toml</code> if <code>XDG_CONFIG_HOME</code> is set, or <code>$HOME/.config/gitlab-pypi.toml</code> otherwise.</dd>

      <dt>Windows</dt>
      <dd><code>%LOCALAPPDATA%\gitlab-pypi\gitlab-pypi.toml</code></dd>
    </dl>

    ### System

    <dl>
      <dt>macOS</dt>
      <dd><code>/Library/Application Support/gitlab-pypi/gitlab-pypi.toml</code></dd>

      <dt>Linux</dt>
      <dd>
        <p>
          <code>&lt;config_dir&gt;/gitlab-pypi/gitlab-pypi.toml</code> where <code>&lt;config_dir&gt;</code> is any of the paths set in <code>$XDG_CONFIG_DIRS</code> paths, defaulting to <code>/etc/xdg</code>
        </p>
        <p>
          <code>/etc/gitlab-pypi.toml</code> is higher priority than the above.
        </p>
      </dd>

      <dt>Windows</dt>
      <dd><code>C:\ProgramData\gitlab-pypi\gitlab-pypi.toml</code></dd>
    </dl>

3.  Create a personal access token with `read_api` scope and add it to the config file:

    ```toml
    ["https://gitlab.com"]
    token = "<token>"
    ```

4.  Configure [`keyring-provider`] in uv:

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

5.  Configure one or more GitLab package indexes

    For example, in `pyproject.toml`:

    ```toml
    [[tool.uv.index]]
    name = "myindex"
    url = "https://gitlab.example.com/api/v4/projects/1/packages/pypi/simple"
    authenticate = "always"
    ```

    **Note**

    You need `authenticate = "always"` for uv to invoke [keyring] when no username is specified. This option is a good idea anyway!

    Alternatively, add the username `__token__` to the URL, but this is not recommended for `pyproject.toml` as you likely want to use a different username in CI, for example.

6.  Done! `keyring-gitlab-pypi` will return your token for URLs that look like package installs.

## Using it in GitLab CI

`$CI_JOB_TOKEN` will be used automatically as long as the index URL matches the running GitLab instance.

In principle this is all you need:

```yaml
variables:
  UV_KEYRING_PROVIDER: subprocess
  UV_TOOL_BIN_DIR: /usr/local/bin

test:
  image: ghcr.io/astral-sh/uv:python3.13-bookworm
  before_script:
    - uv tool install keyring --with keyring-gitlab-pypi
    - uv sync
```

This assumes that you haven't set `UV_INDEX`. (`uv tool` ignores `pyproject.toml` so you don't need to worry about indexes configured there).

It's recommended to constrain the versions:

```bash
printf '%s\n' keyring keyring-gitlab-pypi > keyring-constraints.in
uv pip compile --universal keyring-constraints.in -o keyring-constraints.txt
```

```yaml
variables:
  UV_KEYRING_PROVIDER: subprocess
  UV_TOOL_BIN_DIR: /usr/local/bin

test:
  image: ghcr.io/astral-sh/uv:python3.13-bookworm
  before_script:
    - uv tool install keyring --with keyring-gitlab-pypi -c keyring-constraints.txt
    - uv sync
```

## Motivation

- When using multiple GitLab package indexes, it can be cumbersome to configure them with the same token via environment variables or otherwise.
- [keyring]'s keychain backend on macOS does not support `--mode creds`
- uv will reuse credentials for URLs on the same host, but it feels fragile to just configure one of the indexes and let the credentials cache serve the rest. At the very least, `keyring-gitlab-pypi` is set-and-forget across multiple projects.

[keyring]: https://pypi.org/project/keyring/
[GitLab package registry]: https://docs.gitlab.com/user/packages/pypi_repository/#authenticate-with-the-gitlab-package-registry
[uv]: https://docs.astral.sh/uv/
[`keyring-provider`]: https://docs.astral.sh/uv/reference/settings/#keyring-provider
