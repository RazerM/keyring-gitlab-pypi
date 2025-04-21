import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = "uv"


@nox.session(python=["3.9", "3.10", "3.11", "3.12", "3.13"])
def tests(session: nox.Session) -> None:
    session.run_install(
        "uv",
        "sync",
        "--no-config",
        # "--no-editable",
        # "--reinstall-package=keyring-gitlab-pypi",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )

    if session.posargs:
        tests = session.posargs
    else:
        tests = ["tests/"]

    session.run(
        "pytest",
        "--numprocesses=auto",
        # --cov has an optional value. I don't want to override the source
        # defined in the config file. Take care that the argument after it
        # cannot be interpreted as the option's value.
        "--cov",
        "--cov-report=",
        "--cov-context=test",
        "--cov-append",
        *tests,
    )
