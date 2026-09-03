"""Application entry point — wiring only."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from frwb import appConfig
from frwb.services import taskbarService, themeService
from frwb.ui.appIcons import applicationIcon
from frwb.ui.mainWindow import MainWindow


def main() -> int:
    # A packaged build has no console to print to, so the check that says
    # whether it is intact has to be reachable from the outside.
    if "--selftest" in sys.argv:
        from frwb.selftest import runSelfTest

        index = sys.argv.index("--selftest")
        reportPath = sys.argv[index + 1] if len(sys.argv) > index + 1 else None
        return runSelfTest(reportPath)

    # Before the QApplication: Windows reads the identity when the first
    # window appears, and by then a late call has already been missed.
    taskbarService.applyTaskbarIdentity()

    app = QApplication(sys.argv)
    app.setApplicationName(appConfig.appName)
    app.setApplicationVersion(appConfig.appVersion)
    app.setOrganizationName(appConfig.organizationName)
    # Covers dialogs and anything else that has no icon of its own.
    app.setWindowIcon(applicationIcon())
    # Follows Windows unless the user picked an override under Help > Theme.
    themeService.applyTheme(themeService.loadTheme())

    mainWindow = MainWindow()
    mainWindow.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
