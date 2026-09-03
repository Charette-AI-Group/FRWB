"""Check that a build has everything it needs, and say so.

Worth having because what packaging loses, it loses quietly. A missing icon
gives a blank tile, a missing manual gives a menu item that opens nothing,
and neither crashes. A build can look fine from the outside and be broken in
exactly the ways nobody checks by hand.

So the build runs this and refuses to publish a bundle that fails it:

    frwb.exe --selftest report.txt

Everything here is read-only. It renames nothing, writes only the report it
is asked for, and touches no settings file.
"""

from __future__ import annotations

import sys
from pathlib import Path

from frwb import appConfig


def resourceChecks() -> list[tuple[str, bool, str]]:
    """Every bundled file the app reaches for, and whether it is there."""
    checks: list[tuple[str, bool, str]] = []

    icon = appConfig.iconFile()
    checks.append(("applicationIcon", icon is not None, str(icon or appConfig.resourcesDir)))

    for key in appConfig.actionIconKeys:
        for onDark in (False, True):
            path = appConfig.actionIconFile(key, onDark)
            name = f"{key}-{'onDark' if onDark else 'onLight'}"
            checks.append((f"icon.{name}", path is not None, str(path or "missing")))

    checks.append(("manual", appConfig.manualPath.exists(), str(appConfig.manualPath)))
    return checks


def windowCheck() -> tuple[bool, str]:
    """Build the window offscreen: proof that Qt and every import came up.

    The heaviest thing a packaged build can drop is a Qt plugin, and that
    shows up here rather than as a window that never appears on a machine
    with no console to print the reason to.
    """
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication

        from frwb.ui.mainWindow import MainWindow

        application = QApplication.instance() or QApplication([])
        window = MainWindow()
        title = window.windowTitle()
        wornIcon = not window.windowIcon().isNull()
        window.close()
        del application
    except Exception as exc:  # a build that cannot start must say why
        return False, f"{type(exc).__name__}: {exc}"
    if not title:
        return False, "the window has no title"
    if not wornIcon:
        return False, "the window is not wearing its icon"
    return True, title


def report() -> tuple[str, bool]:
    """The whole report, and whether the build is shippable."""
    lines = [
        f"app={appConfig.appShortName} {appConfig.appVersion}",
        f"platform={sys.platform}",
        f"frozen={appConfig.isFrozen}",
        f"bundleRoot={appConfig.bundleRoot}",
        f"resourcesDir={appConfig.resourcesDir}",
    ]
    passed = True
    for name, found, detail in resourceChecks():
        lines.append(f"{name}={'ok' if found else 'MISSING'}  {detail}")
        passed = passed and found

    windowOk, detail = windowCheck()
    lines.append(f"window={'ok' if windowOk else 'FAILED'}  {detail}")
    passed = passed and windowOk

    lines.append(f"result={'ok' if passed else 'FAILED'}")
    return "\n".join(lines), passed


def runSelfTest(reportPath: str | None = None) -> int:
    text, passed = report()
    if reportPath:
        Path(reportPath).write_text(text, encoding="utf-8")
    print(text)
    return 0 if passed else 1
