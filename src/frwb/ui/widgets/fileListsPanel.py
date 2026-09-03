"""The two panels: the files as they are, and the names they would get.

The lists scroll and select together, so a row on the right is always the
same file as the row on the left. Nothing here touches files: the panel
shows what it is given and says what the user asked for.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from frwb import appConfig
from frwb.models.renameModels import FileEntry, PreviewStatus, RenamePreview, SortKey
from frwb.services import renamePlanService
from frwb.ui import appIcons

sortLabels = {
    SortKey.name: "Name",
    SortKey.created: "Created",
    SortKey.modified: "Modified",
    SortKey.taken: "Photo Taken",
}
noFolderText = "No folder selected"
chooseFolderHint = "Choose a folder to begin."
dateTimeFormat = "%Y-%m-%d %H:%M:%S"
openHint = "Double-click to open the file."


def entryToolTip(entry: FileEntry) -> str:
    taken = entry.takenAt.strftime(dateTimeFormat) if entry.takenAt else "none"
    return (
        f"{entry.path}\n"
        f"Created: {entry.createdAt.strftime(dateTimeFormat)}\n"
        f"Modified: {entry.modifiedAt.strftime(dateTimeFormat)}\n"
        f"Photo taken: {taken}\n"
        f"Size: {entry.sizeBytes:,} bytes\n"
        f"{openHint}"
    )


def renameButtonStyle(onDark: bool) -> str:
    """The Rename button: plain while it cannot run, coloured once it can.

    Both states carry the same border and padding so that becoming ready
    changes the colour and nothing else. Styling only the ready state would
    hand the button a different size the moment it lit up, and shift the row
    with it.
    """
    ready = appConfig.renameReadyOnDark if onDark else appConfig.renameReadyOnLight
    return f"""
        QPushButton#renameButton {{
            border: 1px solid palette(mid);
            border-radius: 4px;
            padding: 5px 14px;
            font-weight: 600;
            background-color: palette(button);
            color: palette(button-text);
        }}
        QPushButton#renameButton:disabled {{
            color: palette(mid);
        }}
        QPushButton#renameButton:enabled {{
            background-color: {ready["background"]};
            border-color: {ready["background"]};
            color: {ready["text"]};
        }}
        QPushButton#renameButton:enabled:hover {{
            background-color: {ready["hover"]};
            border-color: {ready["hover"]};
        }}
        QPushButton#renameButton:enabled:pressed {{
            background-color: {ready["pressed"]};
            border-color: {ready["pressed"]};
        }}
    """


def summaryText(counts: dict[PreviewStatus, int]) -> str:
    total = sum(counts.values())
    parts = [f"{total} files", f"{counts[PreviewStatus.renamed]} to rename"]
    parts.append(f"{counts[PreviewStatus.unchanged]} unchanged")
    if counts[PreviewStatus.skipped]:
        parts.append(f"{counts[PreviewStatus.skipped]} not checked")
    if counts[PreviewStatus.conflict]:
        parts.append(f"{counts[PreviewStatus.conflict]} conflicts")
    if counts[PreviewStatus.invalid]:
        parts.append(f"{counts[PreviewStatus.invalid]} invalid")
    return "  ·  ".join(parts)


def canRename(counts: dict[PreviewStatus, int]) -> tuple[bool, str]:
    """Whether the batch may run, and if not, the reason to show."""
    if counts[PreviewStatus.conflict]:
        return False, "Fix the conflicts shown in red before renaming."
    if counts[PreviewStatus.invalid]:
        return False, "Fix the invalid names shown in orange before renaming."
    if not counts[PreviewStatus.renamed]:
        return False, "No name would change."
    return True, f"Rename {counts[PreviewStatus.renamed]} files."


class FileListsPanel(QWidget):
    chooseFolderRequested = Signal()
    renameRequested = Signal()
    filterChanged = Signal(str)
    sortChanged = Signal(object)  # a SortKey
    checkedChanged = Signal()
    # A row was double-clicked, in either list: the Path of the file behind it.
    fileActivated = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.entries: list[FileEntry] = []
        self.previews: list[RenamePreview] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.buildSourcePanel())
        self.splitter.addWidget(self.buildTargetPanel())
        self.splitter.setChildrenCollapsible(False)
        layout.addWidget(self.splitter, 1)
        self.summaryLabel = QLabel(chooseFolderHint)
        layout.addWidget(self.summaryLabel)
        self.linkLists()
        self.applyIcons()
        self.applyRenameStyle()

    # --- building ----------------------------------------------------------

    def buildSourcePanel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.chooseFolderButton = QPushButton("Choose Folder...")
        self.chooseFolderButton.clicked.connect(self.chooseFolderRequested)
        self.folderLabel = QLabel(noFolderText)
        self.folderLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # Ignored: a long path must not widen the panel, it gets cut instead.
        self.folderLabel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        header.addWidget(self.chooseFolderButton)
        header.addWidget(self.folderLabel, 1)

        options = QHBoxLayout()
        self.filterEdit = QLineEdit(appConfig.defaultFileFilter)
        self.filterEdit.setPlaceholderText("*.jpg; *.png")
        self.filterEdit.setToolTip("Patterns separated by semicolons. Press Enter to apply.")
        self.filterEdit.editingFinished.connect(self.onFilterEdited)
        self.sortCombo = QComboBox()
        for key, label in sortLabels.items():
            self.sortCombo.addItem(label, key)
        self.sortCombo.setToolTip("The order of the list is the order the counter runs in.")
        self.sortCombo.currentIndexChanged.connect(self.onSortPicked)
        self.checkAllButton = QToolButton()
        self.checkAllButton.setText("All")
        self.checkAllButton.clicked.connect(lambda: self.setAllChecked(True))
        self.checkNoneButton = QToolButton()
        self.checkNoneButton.setText("None")
        self.checkNoneButton.clicked.connect(lambda: self.setAllChecked(False))
        options.addWidget(QLabel("Filter:"))
        options.addWidget(self.filterEdit, 1)
        options.addWidget(QLabel("Sort By:"))
        options.addWidget(self.sortCombo)
        options.addWidget(QLabel("Check:"))
        options.addWidget(self.checkAllButton)
        options.addWidget(self.checkNoneButton)

        self.sourceList = QListWidget()
        self.sourceList.setObjectName("sourceList")
        self.sourceList.setAlternatingRowColors(True)
        self.sourceList.itemChanged.connect(self.onSourceItemChanged)
        self.sourceList.itemDoubleClicked.connect(self.onSourceDoubleClicked)

        layout.addLayout(header)
        layout.addLayout(options)
        layout.addWidget(self.sourceList, 1)
        return panel

    def buildTargetPanel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.targetTitle = QLabel("New Names")
        header.addWidget(self.targetTitle, 1)
        self.renameButton = QPushButton("Rename Files")
        self.renameButton.setObjectName("renameButton")
        self.renameButton.setEnabled(False)
        self.renameButton.clicked.connect(self.renameRequested)
        # The glyph has to follow the button's own ground, and the window is
        # not the only thing that enables it, so watch the button itself
        # rather than trusting every caller to say so.
        self.renameButton.installEventFilter(self)
        header.addWidget(self.renameButton)

        self.legendLabel = QLabel("Gray: unchanged.  Red: conflict.  Orange: invalid name.")
        self.legendLabel.setEnabled(False)

        self.targetList = QListWidget()
        self.targetList.setObjectName("targetList")
        self.targetList.setAlternatingRowColors(True)
        self.targetList.itemDoubleClicked.connect(self.onTargetDoubleClicked)

        layout.addLayout(header)
        layout.addWidget(self.legendLabel)
        layout.addWidget(self.targetList, 1)
        return panel

    def linkLists(self) -> None:
        sourceBar = self.sourceList.verticalScrollBar()
        targetBar = self.targetList.verticalScrollBar()
        sourceBar.valueChanged.connect(targetBar.setValue)
        targetBar.valueChanged.connect(sourceBar.setValue)
        self.sourceList.currentRowChanged.connect(self.targetList.setCurrentRow)
        self.targetList.currentRowChanged.connect(self.sourceList.setCurrentRow)

    # --- what the window tells the panel -----------------------------------

    def setFolder(self, folder: Path | None) -> None:
        text = str(folder) if folder else noFolderText
        self.folderLabel.setText(text)
        self.folderLabel.setToolTip(text)

    def setFilterText(self, filterText: str) -> None:
        self.filterEdit.setText(filterText)

    def setSortKey(self, sortKey: SortKey) -> None:
        index = self.sortCombo.findData(sortKey)
        if index >= 0:
            self.sortCombo.setCurrentIndex(index)

    def setEntries(self, entries: list[FileEntry]) -> None:
        """Show the files; a file unchecked before stays unchecked if still here."""
        unchecked = {
            self.sourceList.item(row).text()
            for row in range(self.sourceList.count())
            if self.sourceList.item(row).checkState() != Qt.CheckState.Checked
        }
        self.entries = list(entries)
        self.sourceList.blockSignals(True)
        self.sourceList.clear()
        for entry in self.entries:
            item = QListWidgetItem(entry.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            isChecked = entry.name not in unchecked
            item.setCheckState(Qt.CheckState.Checked if isChecked else Qt.CheckState.Unchecked)
            item.setToolTip(entryToolTip(entry))
            self.sourceList.addItem(item)
        self.sourceList.blockSignals(False)

    def setPreviews(self, previews: list[RenamePreview]) -> None:
        self.previews = list(previews)
        self.targetList.clear()
        for preview in self.previews:
            item = QListWidgetItem(preview.newName)
            item.setToolTip(f"{preview.note or preview.newName}\n{openHint}")
            colour = self.colourFor(preview.status)
            if colour is not None:
                item.setForeground(colour)
            self.targetList.addItem(item)
        counts = renamePlanService.countByStatus(self.previews)
        self.summaryLabel.setText(summaryText(counts))
        allowed, reason = canRename(counts)
        self.renameButton.setEnabled(allowed)
        self.renameButton.setToolTip(reason)

    # --- what the panel tells the window -----------------------------------

    def includedFlags(self) -> list[bool]:
        return [
            self.sourceList.item(row).checkState() == Qt.CheckState.Checked
            for row in range(self.sourceList.count())
        ]

    def setAllChecked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.sourceList.blockSignals(True)
        for row in range(self.sourceList.count()):
            self.sourceList.item(row).setCheckState(state)
        self.sourceList.blockSignals(False)
        self.checkedChanged.emit()

    def onSourceItemChanged(self, _item: QListWidgetItem) -> None:
        self.checkedChanged.emit()

    def onSourceDoubleClicked(self, item: QListWidgetItem) -> None:
        row = self.sourceList.row(item)
        if 0 <= row < len(self.entries):
            self.fileActivated.emit(self.entries[row].path)

    def onTargetDoubleClicked(self, item: QListWidgetItem) -> None:
        """The right list shows names that do not exist yet, so the file on
        the disk is opened: the same one the row on the left stands for."""
        row = self.targetList.row(item)
        if 0 <= row < len(self.previews):
            self.fileActivated.emit(self.previews[row].source)

    def onFilterEdited(self) -> None:
        self.filterChanged.emit(self.filterEdit.text())

    def onSortPicked(self, _index: int) -> None:
        # Qt hands the stored enum back as its plain string value.
        self.sortChanged.emit(SortKey(self.sortCombo.currentData()))

    # --- colours -----------------------------------------------------------

    def colourFor(self, status: PreviewStatus) -> QColor | None:
        if status in (PreviewStatus.unchanged, PreviewStatus.skipped):
            return self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
        if status == PreviewStatus.conflict:
            return QColor(appConfig.conflictColour)
        if status == PreviewStatus.invalid:
            return QColor(appConfig.invalidColour)
        return None

    def applyIcons(self) -> None:
        """The two buttons that carry a glyph, each in the ink it needs."""
        self.chooseFolderButton.setIcon(appIcons.actionIcon("chooseFolder"))
        self.applyRenameIcon()

    def applyRenameIcon(self) -> None:
        """The Rename glyph follows the button's ground, not the window's.

        Ready, the button paints itself deep teal on a light theme and bright
        teal on a dark one - the opposite lightness of the window each time,
        so the ink flips with it or disappears into it.
        """
        onDarkWindow = appIcons.isDarkBackground()
        onDarkButton = not onDarkWindow if self.renameButton.isEnabled() else onDarkWindow
        self.renameButton.setIcon(appIcons.actionIconOn("rename", onDarkButton))

    def applyRenameStyle(self) -> None:
        self.renameButton.setStyleSheet(renameButtonStyle(appIcons.isDarkBackground()))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.renameButton and event.type() == QEvent.Type.EnabledChange:
            self.applyRenameIcon()
        return super().eventFilter(watched, event)

    def changeEvent(self, event: QEvent) -> None:
        # The gray, the glyph ink and the ready colour all come from the
        # palette, which Qt delivers after the theme has been applied.
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self.applyIcons()
            self.applyRenameStyle()
            if self.previews:
                self.setPreviews(self.previews)
