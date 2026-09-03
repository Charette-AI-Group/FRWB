"""Smoke tests for the two file panels."""

from __future__ import annotations

from pathlib import Path

from conftest import makeEntry
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QListWidgetItem

from frwb import appConfig
from frwb.models.renameModels import PreviewStatus, RenamePreview, SortKey
from frwb.ui import appIcons
from frwb.ui.widgets.fileListsPanel import FileListsPanel


def preview(name: str, newName: str, status: PreviewStatus) -> RenamePreview:
    return RenamePreview(Path("C:/photos") / name, newName, status, "note")


def testEntriesAreListedAndChecked(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)

    panel.setEntries([makeEntry("a.jpg"), makeEntry("b.jpg")])

    assert [panel.sourceList.item(i).text() for i in range(2)] == ["a.jpg", "b.jpg"]
    assert panel.includedFlags() == [True, True]
    assert "Created" in panel.sourceList.item(0).toolTip()


def testUncheckingAFileIsRememberedAcrossARefresh(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    panel.setEntries([makeEntry("a.jpg"), makeEntry("b.jpg")])

    with qtbot.waitSignal(panel.checkedChanged, timeout=1000):
        panel.sourceList.item(1).setCheckState(Qt.CheckState.Unchecked)
    panel.setEntries([makeEntry("b.jpg"), makeEntry("c.jpg")])

    assert panel.includedFlags() == [False, True]


def testCheckAllAndNone(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    panel.setEntries([makeEntry("a.jpg"), makeEntry("b.jpg")])

    with qtbot.waitSignal(panel.checkedChanged, timeout=1000):
        panel.checkNoneButton.click()
    assert panel.includedFlags() == [False, False]

    panel.checkAllButton.click()
    assert panel.includedFlags() == [True, True]


def testPreviewsFillTheRightListAndTheSummary(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)

    panel.setPreviews(
        [
            preview("a.jpg", "a_001.jpg", PreviewStatus.renamed),
            preview("b.jpg", "b.jpg", PreviewStatus.unchanged),
        ]
    )

    assert [panel.targetList.item(i).text() for i in range(2)] == ["a_001.jpg", "b.jpg"]
    assert "2 files" in panel.summaryLabel.text()
    assert "1 to rename" in panel.summaryLabel.text()
    assert panel.renameButton.isEnabled()


def testAConflictDisablesRenamingAndSaysWhy(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)

    panel.setPreviews(
        [
            preview("a.jpg", "x.jpg", PreviewStatus.renamed),
            preview("b.jpg", "x.jpg", PreviewStatus.conflict),
        ]
    )

    assert not panel.renameButton.isEnabled()
    assert "conflict" in panel.renameButton.toolTip()
    assert "1 conflicts" in panel.summaryLabel.text()


def testNothingToRenameDisablesTheButton(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)

    panel.setPreviews([preview("a.jpg", "a.jpg", PreviewStatus.unchanged)])

    assert not panel.renameButton.isEnabled()


def testFilterAndSortAreAnnounced(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.filterChanged, timeout=1000) as blocker:
        panel.filterEdit.setText("*.jpg")
        panel.filterEdit.editingFinished.emit()
    assert blocker.args == ["*.jpg"]

    with qtbot.waitSignal(panel.sortChanged, timeout=1000) as blocker:
        panel.setSortKey(SortKey.modified)
    assert blocker.args == [SortKey.modified]


def doubleClickRow(qtbot, listWidget, row: int) -> None:
    """A press first, then the double-click: a view delivers one only after
    the other, and that is the order a real click arrives in anyway."""
    item = listWidget.item(row)
    listWidget.scrollToItem(item)
    center = listWidget.visualItemRect(item).center()
    qtbot.mouseClick(listWidget.viewport(), Qt.MouseButton.LeftButton, pos=center)
    qtbot.mouseDClick(listWidget.viewport(), Qt.MouseButton.LeftButton, pos=center)


def filledPanel(qtbot) -> FileListsPanel:
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.setEntries([makeEntry("a.jpg"), makeEntry("b.jpg")])
    panel.setPreviews(
        [
            preview("a.jpg", "a_001.jpg", PreviewStatus.renamed),
            preview("b.jpg", "b_002.jpg", PreviewStatus.renamed),
        ]
    )
    return panel


def testDoubleClickingTheLeftListAsksForThatFile(qtbot) -> None:
    panel = filledPanel(qtbot)

    with qtbot.waitSignal(panel.fileActivated, timeout=1000) as blocker:
        doubleClickRow(qtbot, panel.sourceList, 1)

    assert blocker.args == [Path("C:/photos/b.jpg")]


def testDoubleClickingTheRightListAsksForTheFileOnDiskNotTheNewName(qtbot) -> None:
    """The right list shows names that do not exist yet; the source opens."""
    panel = filledPanel(qtbot)

    with qtbot.waitSignal(panel.fileActivated, timeout=1000) as blocker:
        doubleClickRow(qtbot, panel.targetList, 0)

    assert blocker.args == [Path("C:/photos/a.jpg")]


def testDoubleClickingEmptySpaceAsksForNothing(qtbot) -> None:
    panel = filledPanel(qtbot)
    orphan = QListWidgetItem("not in any list")

    with qtbot.assertNotEmitted(panel.fileActivated):
        panel.onSourceDoubleClicked(orphan)
        panel.onTargetDoubleClicked(orphan)


def testTheToolTipsSayThatDoubleClickingOpens(qtbot) -> None:
    panel = filledPanel(qtbot)

    assert "Double-click" in panel.sourceList.item(0).toolTip()
    assert "Double-click" in panel.targetList.item(0).toolTip()


# --- the Rename button lighting up ----------------------------------------------


def relativeLuminance(colour: str) -> float:
    """WCAG relative luminance, so the contrast rule can be checked, not assumed."""
    channels = []
    for value in QColor(colour).getRgbF()[:3]:
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrastRatio(first: str, second: str) -> float:
    lighter, darker = sorted((relativeLuminance(first), relativeLuminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def testTheReadyColoursAreReadableOnBothThemes() -> None:
    """The point of two palettes: each has to carry its own text."""
    for palette in (appConfig.renameReadyOnLight, appConfig.renameReadyOnDark):
        for state in ("background", "hover", "pressed"):
            ratio = contrastRatio(palette[state], palette["text"])
            assert ratio >= 4.5, f"{palette[state]} on {palette['text']} is only {ratio:.2f}:1"


def testTheTwoThemesUseDifferentReadyColours() -> None:
    light, dark = appConfig.renameReadyOnLight, appConfig.renameReadyOnDark

    assert light["background"] != dark["background"]
    # Deep under white on a light theme, bright under near-black on a dark one.
    assert relativeLuminance(light["background"]) < relativeLuminance(dark["background"])


def testTheButtonIsColouredOnlyWhileItCanRun(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    style = panel.renameButton.styleSheet()

    assert appConfig.renameReadyOnLight["background"] in style or (
        appConfig.renameReadyOnDark["background"] in style
    )
    # The colour is bound to the enabled state, not painted on unconditionally.
    assert "QPushButton#renameButton:enabled" in style
    assert not panel.renameButton.isEnabled()


def testTheReadyColourFollowsTheTheme(qtbot, monkeypatch) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)

    monkeypatch.setattr(appIcons, "isDarkBackground", lambda: True)
    panel.applyRenameStyle()
    assert appConfig.renameReadyOnDark["background"] in panel.renameButton.styleSheet()

    monkeypatch.setattr(appIcons, "isDarkBackground", lambda: False)
    panel.applyRenameStyle()
    assert appConfig.renameReadyOnLight["background"] in panel.renameButton.styleSheet()


def testBothStatesKeepTheSameBox(qtbot) -> None:
    """Becoming ready must change the colour and not the size."""
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    panel.show()
    disabled = panel.renameButton.sizeHint()

    panel.setPreviews([preview("a.jpg", "b.jpg", PreviewStatus.renamed)])

    assert panel.renameButton.isEnabled()
    assert panel.renameButton.sizeHint() == disabled


def testTheGlyphFollowsTheButtonGroundNotTheWindow(qtbot, monkeypatch) -> None:
    """Ready, the button is the opposite lightness of the window it sits in."""
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    asked: list[bool] = []
    monkeypatch.setattr(appIcons, "isDarkBackground", lambda: False)
    monkeypatch.setattr(
        appIcons, "actionIconOn", lambda key, onDark: asked.append(onDark) or QIcon()
    )

    panel.applyRenameIcon()
    assert asked == [False], "disabled, so it sits on the window's own ground"

    panel.setPreviews([preview("a.jpg", "b.jpg", PreviewStatus.renamed)])
    assert asked[-1] is True, "ready on a light theme means a dark button"


def testEnablingTheButtonAnywhereRedrawsItsGlyph(qtbot, monkeypatch) -> None:
    """The window enables it too, while a rename runs and when one ends."""
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    asked: list[bool] = []
    monkeypatch.setattr(appIcons, "isDarkBackground", lambda: False)
    monkeypatch.setattr(
        appIcons, "actionIconOn", lambda key, onDark: asked.append(onDark) or QIcon()
    )

    panel.renameButton.setEnabled(True)

    assert asked and asked[-1] is True


def testTheListsSelectTogether(qtbot) -> None:
    panel = FileListsPanel()
    qtbot.addWidget(panel)
    panel.setEntries([makeEntry("a.jpg"), makeEntry("b.jpg")])
    panel.setPreviews(
        [
            preview("a.jpg", "a.jpg", PreviewStatus.unchanged),
            preview("b.jpg", "b.jpg", PreviewStatus.unchanged),
        ]
    )

    panel.sourceList.setCurrentRow(1)

    assert panel.targetList.currentRow() == 1
