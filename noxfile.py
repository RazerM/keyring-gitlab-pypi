import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = "uv"


@nox.session(python=["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"])
def tests(session: nox.Session) -> None:
    session.run_install(
        "uv",
        "sync",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )

    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "--numprocesses=auto",
        *session.posargs,
    )


@nox.session(python="3.13")
def typing(session: nox.Session) -> None:
    session.run_install(
        "uv",
        "sync",
        "--group=typing",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )
    session.run(
        "mypy",
        "src/keyrings",
        "tests",
        # This environment variable is required in combination with
        # explicit_package_bases in pyproject.toml so that namespace packages work.
        env={"MYPYPATH": "src"},
    )
