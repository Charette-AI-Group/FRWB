"""Where the settings and the undo log live, per platform.

Each platform has a place applications are expected to put this, and using
the wrong one is not a crash: it is a folder appearing in the middle of
somebody's home directory, which they then have to wonder about.
"""

from __future__ import annotations

from pathlib import Path

from frwb import appConfig


def rootFor(monkeypatch, platform: str, **environment: str) -> Path:
    monkeypatch.setattr(appConfig.sys, "platform", platform)
    for name in ("APPDATA", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    return appConfig.userDataRoot()


def testWindowsUsesAppData(monkeypatch) -> None:
    root = rootFor(monkeypatch, "win32", APPDATA=r"C:\Users\Someone\AppData\Roaming")

    assert root == Path(r"C:\Users\Someone\AppData\Roaming")


def testWindowsWithoutAppDataStillLandsSomewhereSensible(monkeypatch) -> None:
    """The variable is always set in practice, but never is not a crash."""
    root = rootFor(monkeypatch, "win32")

    assert root == Path.home() / "AppData" / "Roaming"


def testMacosUsesApplicationSupport(monkeypatch) -> None:
    """Not the home folder, which is what the old fallback gave it."""
    root = rootFor(monkeypatch, "darwin")

    assert root == Path.home() / "Library" / "Application Support"
    assert root != Path.home()


def testLinuxFollowsXdg(monkeypatch) -> None:
    root = rootFor(monkeypatch, "linux", XDG_CONFIG_HOME="/home/someone/.config")

    assert root == Path("/home/someone/.config")


def testLinuxWithoutXdgUsesTheDefault(monkeypatch) -> None:
    root = rootFor(monkeypatch, "linux")

    assert root == Path.home() / ".config"


def testTheAppFolderHangsOffWhicheverRootApplies() -> None:
    """The two file paths are not checked here: an autouse fixture redirects
    them into tmp_path so no test can write to a real settings file."""
    assert appConfig.appDataDir == appConfig.userDataRoot() / appConfig.appName
    assert appConfig.appDataDir.name == appConfig.appName
