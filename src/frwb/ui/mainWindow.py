"""Main application window: composes the panels and runs the workers."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDesktopServices,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from frwb import appConfig
from frwb.models.renameModels import (
    FileEntry,
    RenameOperation,
    RenamePreview,
    RenameResult,
    SortKey,
)
from frwb.services import (
    fileOpenService,
    fileScanService,
    renameExecuteService,
    renamePlanService,
    themeService,
    workbenchStateService,
)
from frwb.services.fileScanWorker import FileScanWorker
from frwb.services.manualWorker import ManualWorker
from frwb.services.renameWorker import RenameWorker
from frwb.ui import appIcons
from frwb.ui.dialogs.aboutDialog import showAbout
from frwb.ui.dialogs.errorDialog import showError
from frwb.ui.widgets.fileListsPanel import FileListsPanel
from frwb.ui.widgets.renameControlsPanel import RenameControlsPanel
from frwb.ui.widgets.reportingView import ReportingView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(appConfig.windowTitle)
        self.setWindowIcon(appIcons.applicationIcon())
        self.resize(appConfig.defaultWindowWidth, appConfig.defaultWindowHeight)
        self.manualWorker: ManualWorker | None = None
        self.scanWorker: FileScanWorker | None = None
        self.renameWorker: RenameWorker | None = None
        # Every file in the folder, before the filter; the panel holds the rest.
        self.entries: list[FileEntry] = []
        self.previews: list[RenamePreview] = []
        self.state = workbenchStateService.loadState()

        self.buildMenuBar()
        self.buildCentralWidget()
        self.applyActionIcons()
        self.previewTimer = QTimer(self)
        self.previewTimer.setSingleShot(True)
        self.previewTimer.setInterval(appConfig.previewDelayMilliseconds)
        self.previewTimer.timeout.connect(self.refreshPreview)
        self.updateUndoAction()
        self.showStatus("Ready")

        if self.state.folder and Path(self.state.folder).is_dir():
            self.loadFolder(Path(self.state.folder))

    def buildMenuBar(self) -> None:
        # Menus are kept as attributes: features can extend them later, and it
        # prevents the Python wrappers from being garbage-collected.
        fileMenu = self.fileMenu = self.menuBar().addMenu("&File")

        self.chooseFolderAction = QAction("&Choose Folder...", self)
        self.chooseFolderAction.setShortcut(QKeySequence.StandardKey.Open)
        self.chooseFolderAction.triggered.connect(self.onChooseFolder)
        fileMenu.addAction(self.chooseFolderAction)

        self.refreshAction = QAction("&Refresh", self)
        self.refreshAction.setShortcut(QKeySequence.StandardKey.Refresh)
        self.refreshAction.triggered.connect(self.onRefresh)
        fileMenu.addAction(self.refreshAction)

        fileMenu.addSeparator()

        self.renameAction = QAction("&Rename Files", self)
        self.renameAction.setShortcut(QKeySequence("Ctrl+R"))
        self.renameAction.setEnabled(False)
        self.renameAction.triggered.connect(self.onRenameFiles)
        fileMenu.addAction(self.renameAction)

        self.undoAction = QAction("&Undo Last Rename", self)
        self.undoAction.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        self.undoAction.triggered.connect(self.onUndoLastRename)
        fileMenu.addAction(self.undoAction)

        fileMenu.addSeparator()

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setShortcut(QKeySequence("Ctrl+Q"))
        self.exitAction.triggered.connect(self.close)
        fileMenu.addAction(self.exitAction)

        self.buildHelpMenu()

    def buildHelpMenu(self) -> None:
        helpMenu = self.helpMenu = self.menuBar().addMenu("&Help")

        self.themeMenu = helpMenu.addMenu("&Theme")
        self.themeGroup = QActionGroup(self)
        self.themeGroup.setExclusive(True)
        self.themeActions: dict[str, QAction] = {}
        activeTheme = themeService.loadTheme()
        for theme in themeService.themeChoices:
            action = QAction(themeService.themeLabels[theme], self)
            action.setCheckable(True)
            action.setChecked(theme == activeTheme)
            action.triggered.connect(partial(self.onThemeChosen, theme))
            self.themeGroup.addAction(action)
            self.themeMenu.addAction(action)
            self.themeActions[theme] = action

        helpMenu.addSeparator()

        self.manualAction = QAction("User &Manual...", self)
        self.manualAction.setShortcut(QKeySequence.StandardKey.HelpContents)  # F1
        self.manualAction.triggered.connect(self.onHelpManual)
        helpMenu.addAction(self.manualAction)

        self.aboutAction = QAction("&About", self)
        self.aboutAction.triggered.connect(self.onHelpAbout)
        helpMenu.addAction(self.aboutAction)

    def buildCentralWidget(self) -> None:
        self.controlsPanel = RenameControlsPanel()
        self.controlsPanel.applySettings(self.state.settings)
        self.controlsPanel.settingsChanged.connect(self.schedulePreview)

        self.listsPanel = FileListsPanel()
        self.listsPanel.setFilterText(self.state.fileFilter)
        self.listsPanel.setSortKey(self.state.sortKey)
        self.listsPanel.chooseFolderRequested.connect(self.onChooseFolder)
        self.listsPanel.renameRequested.connect(self.onRenameFiles)
        self.listsPanel.filterChanged.connect(self.onFilterChanged)
        self.listsPanel.sortChanged.connect(self.onSortChanged)
        self.listsPanel.checkedChanged.connect(self.schedulePreview)
        self.listsPanel.fileActivated.connect(self.onFileActivated)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.controlsPanel)
        layout.addWidget(self.listsPanel, 1)
        self.setCentralWidget(central)

    def applyActionIcons(self) -> None:
        """Give the menu commands their glyphs, in this theme's ink."""
        for action, key in (
            (self.chooseFolderAction, "chooseFolder"),
            (self.refreshAction, "refresh"),
            (self.renameAction, "rename"),
            (self.undoAction, "undo"),
        ):
            action.setIcon(appIcons.actionIcon(key))

    def changeEvent(self, event: QEvent) -> None:
        """Redraw the glyphs when the theme changes.

        Here rather than in the theme handler: Qt delivers the new palette
        after the theme is applied, so a glyph chosen while handling the menu
        click is chosen from the colours being replaced.
        """
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self.applyActionIcons()

    def connectView(self, view: ReportingView) -> None:
        """Wire a view's status and failures into this window."""
        view.statusMessage.connect(self.showStatus)
        view.errorMessage.connect(self.showError)

    def showStatus(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def showError(self, title: str, message: str) -> None:
        """Kept a method so tests can watch for it without a dialog opening."""
        showError(self, title, message)

    def confirm(self, title: str, question: str) -> bool:
        """Kept a method so tests can answer without a dialog opening."""
        answer = QMessageBox.question(self, title, question)
        return answer == QMessageBox.StandardButton.Yes

    # --- the folder --------------------------------------------------------

    def onChooseFolder(self) -> None:
        start = self.state.folder or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Choose Working Folder", start)
        if chosen:
            self.loadFolder(Path(chosen))

    def onRefresh(self) -> None:
        if self.state.folder:
            self.loadFolder(Path(self.state.folder))
        else:
            self.showStatus("Choose a folder first.")

    def loadFolder(self, folder: Path) -> None:
        if self.scanWorker is not None:
            self.showStatus("Still reading the previous folder, one moment.")
            return
        self.state.folder = str(folder)
        self.saveState()
        self.listsPanel.setFolder(folder)
        self.showStatus(f"Reading {folder}...")
        worker = FileScanWorker(folder, parent=self)
        worker.scanned.connect(self.onFolderScanned)
        worker.failed.connect(self.onScanFailed)
        worker.finished.connect(self.onScanFinished)
        self.scanWorker = worker
        worker.start()

    def onFolderScanned(self, entries: list[FileEntry]) -> None:
        self.entries = entries
        self.showStatus(f"{len(entries)} files in {self.state.folder}")
        self.rebuildEntries()

    def onScanFailed(self, message: str) -> None:
        self.entries = []
        self.rebuildEntries()
        self.showError("Could Not Read Folder", message)

    def onScanFinished(self) -> None:
        if self.scanWorker is not None:
            self.scanWorker.deleteLater()
            self.scanWorker = None

    def rebuildEntries(self) -> None:
        visible = fileScanService.filterEntries(self.entries, self.state.fileFilter)
        visible = fileScanService.sortEntries(visible, self.state.sortKey)
        self.listsPanel.setEntries(visible)
        self.refreshPreview()

    def onFileActivated(self, path: Path) -> None:
        """A double-click in either list opens the file, as Explorer does."""
        problem = fileOpenService.openFile(path)
        if problem:
            self.showError("Could Not Open File", problem)
            return
        self.showStatus(f"Opening {path.name}...")

    def onFilterChanged(self, filterText: str) -> None:
        self.state.fileFilter = filterText.strip() or appConfig.defaultFileFilter
        self.saveState()
        self.rebuildEntries()

    def onSortChanged(self, sortKey: SortKey) -> None:
        self.state.sortKey = sortKey
        self.saveState()
        self.rebuildEntries()

    # --- the preview -------------------------------------------------------

    def schedulePreview(self) -> None:
        self.previewTimer.start()

    def refreshPreview(self) -> None:
        self.state.settings = self.controlsPanel.currentSettings()
        self.saveState()
        self.previews = renamePlanService.buildPreviews(
            self.listsPanel.entries,
            self.state.settings,
            existingNames=[entry.name for entry in self.entries],
            included=self.listsPanel.includedFlags(),
        )
        self.listsPanel.setPreviews(self.previews)
        self.renameAction.setEnabled(self.listsPanel.renameButton.isEnabled())

    def saveState(self) -> None:
        workbenchStateService.saveState(self.state)

    # --- renaming ----------------------------------------------------------

    def onRenameFiles(self) -> None:
        operations = renameExecuteService.operationsFrom(self.previews)
        if not operations:
            self.showStatus("Nothing to rename.")
            return
        question = f"Rename {len(operations)} files in\n{self.state.folder}?"
        if not self.confirm("Rename Files", question):
            return
        self.startRename(operations, isUndo=False)

    def onUndoLastRename(self) -> None:
        operations = renameExecuteService.readUndoLog(appConfig.undoLogFile)
        if not operations:
            self.showStatus("Nothing to undo.")
            return
        question = f"Put {len(operations)} files back to their previous names?"
        if not self.confirm("Undo Last Rename", question):
            return
        self.startRename(renameExecuteService.reversedOperations(operations), isUndo=True)

    def startRename(self, operations: list[RenameOperation], isUndo: bool) -> None:
        if self.renameWorker is not None:
            self.showStatus("A rename is already running.")
            return
        self.setRenameInProgress(True)
        self.showStatus(f"Renaming {len(operations)} files...")
        worker = RenameWorker(operations, parent=self)
        worker.completed.connect(partial(self.onRenameCompleted, isUndo=isUndo))
        worker.finished.connect(self.onRenameFinished)
        self.renameWorker = worker
        worker.start()

    def onRenameCompleted(self, result: RenameResult, isUndo: bool = False) -> None:
        if isUndo:
            renameExecuteService.clearUndoLog(appConfig.undoLogFile)
            self.showStatus(f"Put {len(result.applied)} files back.")
        else:
            if result.applied:
                renameExecuteService.writeUndoLog(result.applied, appConfig.undoLogFile)
            self.showStatus(f"Renamed {len(result.applied)} files.")
        if result.failed:
            self.showError("Some Files Were Not Renamed", "\n".join(result.failed))
        self.updateUndoAction()
        if self.state.folder:
            self.loadFolder(Path(self.state.folder))

    def onRenameFinished(self) -> None:
        if self.renameWorker is not None:
            self.renameWorker.deleteLater()
            self.renameWorker = None
        self.setRenameInProgress(False)

    def setRenameInProgress(self, busy: bool) -> None:
        self.listsPanel.renameButton.setEnabled(not busy and bool(self.previews))
        self.renameAction.setEnabled(not busy and self.listsPanel.renameButton.isEnabled())
        self.controlsPanel.setEnabled(not busy)

    def updateUndoAction(self) -> None:
        self.undoAction.setEnabled(appConfig.undoLogFile.exists())

    # --- help --------------------------------------------------------------

    def onThemeChosen(self, theme: str) -> None:
        themeService.saveTheme(theme)
        themeService.applyTheme(theme)
        if theme == themeService.systemTheme:
            self.showStatus("Theme follows the Windows setting.")
        else:
            self.showStatus(f"{theme.capitalize()} theme applied.")

    def onHelpManual(self) -> None:
        """Open the manual, preferring the published copy when there is one."""
        if self.manualWorker is not None:
            return
        self.manualAction.setEnabled(False)
        self.showStatus("Looking for the manual...")
        worker = ManualWorker(parent=self)
        worker.resolved.connect(self.openManual)
        worker.finished.connect(self.onManualCheckFinished)
        self.manualWorker = worker
        worker.start()

    def openManual(self, publishedIsReachable: bool) -> None:
        if publishedIsReachable and QDesktopServices.openUrl(QUrl(appConfig.manualUrl)):
            self.showStatus("The manual is opening in your browser.")
            return
        local = appConfig.manualPath
        if local.exists() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(local))):
            self.showStatus(f"Opening the local copy, {local}")
            return
        QMessageBox.information(
            self,
            "User Manual",
            "Could not open the manual. It is at:\n\n"
            f"{appConfig.manualUrl or '(nothing published)'}\n\n{local}",
        )

    def onManualCheckFinished(self) -> None:
        if self.manualWorker is not None:
            self.manualWorker.deleteLater()
            self.manualWorker = None
        self.manualAction.setEnabled(True)

    def onHelpAbout(self) -> None:
        if showAbout(self):
            self.showStatus("Thank you - the donation page is opening in your browser.")

    def closeEvent(self, event: QCloseEvent) -> None:
        # A thread running into interpreter shutdown turns a clean exit into a crash.
        for worker in (self.manualWorker, self.scanWorker, self.renameWorker):
            if worker is not None:
                worker.wait(int(appConfig.manualTimeoutSeconds * 1000) + 1000)
        super().closeEvent(event)
