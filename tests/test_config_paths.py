from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import MonkeyPatch

from keyrings.gitlab_pypi import system_config_paths, user_config_path


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
