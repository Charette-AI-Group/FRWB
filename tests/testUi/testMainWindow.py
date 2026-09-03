"""Smoke tests for the main window, including the folder-to-rename path."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from frwb import appConfig
from frwb.services import themeService
from frwb.ui.mainWindow import MainWindow


def testMainWindowOpens(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()

    assert mainWindow.isVisible()
    assert mainWindow.windowTitle() == "FRWB - File Rename Processing Workbench"
    assert mainWindow.statusBar().currentMessage() == "Ready"
    assert not mainWindow.renameAction.isEnabled()
    assert not mainWindow.undoAction.isEnabled()


def testMenuBarStructure(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    menuTitles = [action.text() for action in mainWindow.menuBar().actions()]
    assert menuTitles == ["&File", "&Help"]

    fileItems = [a.text() for a in mainWindow.fileMenu.actions() if not a.isSeparator()]
    assert fileItems == [
        "&Choose Folder...",
        "&Refresh",
        "&Rename Files",
        "&Undo Last Rename",
        "E&xit",
    ]

    helpItems = [a.text() for a in mainWindow.helpMenu.actions() if not a.isSeparator()]
    assert helpItems == ["&Theme", "User &Manual...", "&About"]


def testThemeMenuOffersSystemLightDark(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    labels = [a.text() for a in mainWindow.themeMenu.actions()]
    assert labels == ["Use &System Theme", "&Light", "&Dark"]
    assert mainWindow.themeActions[themeService.systemTheme].isChecked()


def testChoosingDarkAppliesAndRemembersIt(qtbot, observableColorScheme) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    mainWindow.themeActions[themeService.darkTheme].trigger()

    assert themeService.loadTheme() == themeService.darkTheme
    assert "Dark theme applied" in mainWindow.statusBar().currentMessage()
    if observableColorScheme:
        assert themeService.currentColorScheme() == Qt.ColorScheme.Dark


def testRefreshWithoutAFolderIsANudgeNotAFailure(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    mainWindow.refreshAction.trigger()

    assert mainWindow.statusBar().currentMessage() == "Choose a folder first."


# --- the folder-to-rename path --------------------------------------------------


@pytest.fixture
def folder(tmp_path) -> Path:
    """A folder of its own: tmp_path also holds the isolated settings file."""
    made = tmp_path / "files"
    made.mkdir()
    return made


def waitForScan(qtbot, mainWindow: MainWindow, count: int) -> None:
    qtbot.waitUntil(lambda: mainWindow.listsPanel.sourceList.count() == count, timeout=5000)
    qtbot.waitUntil(lambda: mainWindow.scanWorker is None, timeout=5000)


def targetNames(mainWindow: MainWindow) -> list[str]:
    targetList = mainWindow.listsPanel.targetList
    return [targetList.item(i).text() for i in range(targetList.count())]


def testLoadingAFolderFillsBothPanels(qtbot, folder) -> None:
    (folder / "b.txt").write_text("b")
    (folder / "a.txt").write_text("a")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    mainWindow.loadFolder(folder)
    waitForScan(qtbot, mainWindow, 2)

    sourceList = mainWindow.listsPanel.sourceList
    assert [sourceList.item(i).text() for i in range(2)] == ["a.txt", "b.txt"]
    assert targetNames(mainWindow) == ["a.txt", "b.txt"]
    assert "2 files" in mainWindow.statusBar().currentMessage()
    assert str(folder) in mainWindow.listsPanel.folderLabel.text()


def testChangingThePatternUpdatesTheRightPanel(qtbot, folder) -> None:
    (folder / "a.txt").write_text("a")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.loadFolder(folder)
    waitForScan(qtbot, mainWindow, 1)

    mainWindow.controlsPanel.patternEdit.setText("{name}_{n}")

    qtbot.waitUntil(lambda: targetNames(mainWindow) == ["a_001.txt"], timeout=5000)
    assert mainWindow.renameAction.isEnabled()


def testRenamingAndUndoingTouchTheDisk(qtbot, folder, monkeypatch) -> None:
    (folder / "a.txt").write_text("a")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    monkeypatch.setattr(mainWindow, "confirm", lambda title, question: True)
    mainWindow.loadFolder(folder)
    waitForScan(qtbot, mainWindow, 1)
    mainWindow.controlsPanel.patternEdit.setText("{name}_{n}")
    qtbot.waitUntil(lambda: targetNames(mainWindow) == ["a_001.txt"], timeout=5000)

    mainWindow.onRenameFiles()

    qtbot.waitUntil(lambda: (folder / "a_001.txt").exists(), timeout=5000)
    qtbot.waitUntil(lambda: mainWindow.renameWorker is None, timeout=5000)
    waitForScan(qtbot, mainWindow, 1)
    assert appConfig.undoLogFile.exists()
    assert mainWindow.undoAction.isEnabled()
    assert "Renamed 1 files" in mainWindow.statusBar().currentMessage() or (
        "1 files in" in mainWindow.statusBar().currentMessage()
    )

    mainWindow.onUndoLastRename()

    qtbot.waitUntil(lambda: (folder / "a.txt").exists(), timeout=5000)
    qtbot.waitUntil(lambda: mainWindow.renameWorker is None, timeout=5000)
    assert not appConfig.undoLogFile.exists()


def testDecliningTheConfirmationRenamesNothing(qtbot, folder, monkeypatch) -> None:
    (folder / "a.txt").write_text("a")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    monkeypatch.setattr(mainWindow, "confirm", lambda title, question: False)
    mainWindow.loadFolder(folder)
    waitForScan(qtbot, mainWindow, 1)
    mainWindow.controlsPanel.patternEdit.setText("{name}_{n}")
    qtbot.waitUntil(lambda: targetNames(mainWindow) == ["a_001.txt"], timeout=5000)

    mainWindow.onRenameFiles()

    assert (folder / "a.txt").exists()
    assert mainWindow.renameWorker is None


def testAMissingFolderIsReportedInADialog(qtbot, folder, monkeypatch) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    shown: list[str] = []
    monkeypatch.setattr(mainWindow, "showError", lambda title, message: shown.append(message))

    mainWindow.loadFolder(folder / "gone")

    qtbot.waitUntil(lambda: bool(shown), timeout=5000)
    qtbot.waitUntil(lambda: mainWindow.scanWorker is None, timeout=5000)
    assert "gone" in shown[0]


def testTheLastFolderIsReopenedNextTime(qtbot, folder) -> None:
    (folder / "a.txt").write_text("a")
    first = MainWindow()
    qtbot.addWidget(first)
    first.loadFolder(folder)
    waitForScan(qtbot, first, 1)

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    waitForScan(qtbot, reopened, 1)

    assert str(folder) in reopened.listsPanel.folderLabel.text()


def testDoubleClickingAFileOpensIt(qtbot, folder, monkeypatch) -> None:
    (folder / "a.txt").write_text("a")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.loadFolder(folder)
    waitForScan(qtbot, mainWindow, 1)
    opened: list[Path] = []
    monkeypatch.setattr(
        "frwb.ui.mainWindow.fileOpenService.openFile",
        lambda path: opened.append(path) or "",
    )

    mainWindow.listsPanel.fileActivated.emit(folder / "a.txt")

    assert opened == [folder / "a.txt"]
    assert mainWindow.statusBar().currentMessage() == "Opening a.txt..."


def testAFileThatCannotBeOpenedGoesToADialog(qtbot, folder, monkeypatch) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        mainWindow, "showError", lambda title, message: shown.append((title, message))
    )
    monkeypatch.setattr(
        "frwb.ui.mainWindow.fileOpenService.openFile", lambda path: "It is gone."
    )

    mainWindow.onFileActivated(folder / "gone.txt")

    assert shown == [("Could Not Open File", "It is gone.")]


# --- help ----------------------------------------------------------------------


def testAboutOpensTheDialogAndReportsADonation(qtbot, monkeypatch) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    monkeypatch.setattr("frwb.ui.mainWindow.showAbout", lambda parent: True)

    mainWindow.onHelpAbout()

    assert "donation page" in mainWindow.statusBar().currentMessage()


def openedUrls(monkeypatch) -> list[str]:
    opened: list[str] = []
    monkeypatch.setattr(
        "frwb.ui.mainWindow.QDesktopServices.openUrl",
        lambda url: opened.append(url.toString()) or True,
    )
    return opened


def testManualHasTheStandardHelpShortcut(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    assert mainWindow.manualAction.shortcut() == QKeySequence.StandardKey.HelpContents


def testTheManualShipsWithTheApp() -> None:
    """The local copy is the offline fallback, so it has to be real."""
    assert appConfig.manualPath.exists()
    assert appConfig.manualPath.read_text(encoding="utf-8").strip()


def testThePublishedManualIsPointedAtTheFileThatExists() -> None:
    """A published address that 404s costs a wait and then the wrong answer.

    Checked by construction rather than over the network: the suite must not
    need a connection, and what can go wrong here is the path drifting from
    manualPath, not GitHub going away.
    """
    assert appConfig.manualUrl.startswith(appConfig.repoUrl)
    assert appConfig.manualUrl.endswith("/docs/manual/README.md")

    relative = appConfig.manualPath.relative_to(appConfig.projectRoot).as_posix()
    assert appConfig.manualUrl.endswith(f"/{relative}"), "the two copies have drifted apart"


def testTheLocalCopyIsOpenedWhenNothingIsPublished(qtbot, monkeypatch) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    opened = openedUrls(monkeypatch)

    mainWindow.openManual(publishedIsReachable=False)

    assert len(opened) == 1
    assert opened[0].startswith("file:")
    assert opened[0].endswith("README.md")


def testAMissingManualLeavesTheReaderAnAddress(qtbot, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(appConfig, "manualPath", tmp_path / "gone.md")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    openedUrls(monkeypatch)
    shown: list[str] = []
    monkeypatch.setattr(
        "frwb.ui.mainWindow.QMessageBox.information",
        lambda parent, title, text: shown.append(text),
    )

    mainWindow.openManual(publishedIsReachable=False)

    assert shown and "gone.md" in shown[0]


def testTheManualCheckRunsOffTheInterfaceThread(qtbot, monkeypatch) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    openedUrls(monkeypatch)

    with qtbot.waitSignal(mainWindow.manualAction.changed, timeout=5000):
        mainWindow.onHelpManual()
    assert not mainWindow.manualAction.isEnabled()

    assert mainWindow.manualWorker is not None
    mainWindow.manualWorker.wait(5000)
    qtbot.waitUntil(lambda: mainWindow.manualWorker is None, timeout=5000)
    assert mainWindow.manualAction.isEnabled()
