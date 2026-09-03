"""The application icon and the command glyphs.

Two things are worth pinning: that every command actually gets a glyph - a
guarded line repeated four times is how three of them end up without one -
and that each .ico really carries every size it claims, because a 16 px
entry made by shrinking a 64 px one is mush and nothing else would notice.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PySide6.QtGui import QIcon, QPalette

from frwb import appConfig
from frwb.ui import appIcons
from frwb.ui.mainWindow import MainWindow

#: what tools/makeIcons.py draws into each kind of file
applicationSizes = {16, 24, 32, 48, 64, 128, 256}
actionSizes = {16, 24, 32, 48, 64}
regenerate = "run: python tools/makeIcons.py"


def icoSizes(path: Path) -> set[int]:
    """The sizes an .ico advertises, read from its directory entries."""
    data = path.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    assert reserved == 0 and kind == 1, f"{path.name} is not an .ico"
    sizes = set()
    for index in range(count):
        width, height = struct.unpack_from("<BB", data, 6 + index * 16)[:2]
        # 0 means 256 in the ICO format, which is why 256 needs the special
        # case rather than overflowing a byte
        sizes.add(width or 256)
        assert (height or 256) == (width or 256), "icons must be square"
    return sizes


# --- the files -----------------------------------------------------------------


def testTheApplicationIconExists() -> None:
    assert appConfig.iconFile() is not None, regenerate


def testTheWindowsIconCarriesEverySize() -> None:
    """By name, not through iconFile(), which answers differently on macOS."""
    ico = appConfig.resourcesDir / f"{appConfig.applicationIconStem}.ico"

    assert ico.is_file(), regenerate
    assert icoSizes(ico) == applicationSizes


def testTheMacosIconIsALargePng(qapp) -> None:
    png = appConfig.resourcesDir / f"{appConfig.applicationIconStem}.png"

    assert png.is_file(), regenerate
    sizes = QIcon(str(png)).availableSizes()
    assert sizes, "unreadable as an icon"
    assert sizes[0].width() == 1024, "macOS wants the big one"


@pytest.mark.parametrize("key", appConfig.actionIconKeys)
@pytest.mark.parametrize("onDark", [False, True])
def testEveryCommandHasAGlyphForBothThemes(key: str, onDark: bool) -> None:
    path = appConfig.actionIconFile(key, onDark)

    assert path is not None, regenerate
    assert icoSizes(path) == actionSizes


def testTheTwoInksAreActuallyDifferentFiles() -> None:
    """One file used for both themes would be invisible in one of them."""
    for key in appConfig.actionIconKeys:
        light = appConfig.actionIconFile(key, onDark=False)
        dark = appConfig.actionIconFile(key, onDark=True)
        assert light.read_bytes() != dark.read_bytes(), key


def testTheGlyphsDifferFromEachOther() -> None:
    """Four commands wearing one drawing is worse than none at all."""
    drawings = {
        key: appConfig.actionIconFile(key, onDark=False).read_bytes()
        for key in appConfig.actionIconKeys
    }

    assert len(set(drawings.values())) == len(appConfig.actionIconKeys)


def testAnUnknownCommandIsRefused() -> None:
    with pytest.raises(ValueError, match="unknown action icon"):
        appConfig.actionIconFile("nope", onDark=False)


# --- what the application does with them ----------------------------------------


def testTheInkFollowsTheWindowColour(qapp, monkeypatch) -> None:
    """Read from the palette, so "follow Windows" is answered too."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, "#101010")
    monkeypatch.setattr(appIcons.QGuiApplication, "palette", staticmethod(lambda: palette))
    assert appIcons.isDarkBackground()

    palette.setColor(QPalette.ColorRole.Window, "#F5F5F5")
    assert not appIcons.isDarkBackground()


def testAMissingFileGivesAnEmptyIconRatherThanAnError(qapp, monkeypatch, tmp_path) -> None:
    """A checkout that has not run the generator still starts."""
    monkeypatch.setattr(appConfig, "resourcesDir", tmp_path)

    assert appIcons.applicationIcon().isNull()
    assert appIcons.actionIcon("refresh").isNull()


def testTheWindowWearsTheApplicationIcon(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    assert not mainWindow.windowIcon().isNull()


def testEveryMenuCommandWearsItsGlyph(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    for action in (
        mainWindow.chooseFolderAction,
        mainWindow.refreshAction,
        mainWindow.renameAction,
        mainWindow.undoAction,
    ):
        assert not action.icon().isNull(), action.text()


def testTheButtonsWearTheirGlyphs(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    assert not mainWindow.listsPanel.chooseFolderButton.icon().isNull()
    assert not mainWindow.listsPanel.renameButton.icon().isNull()


def testChangingTheThemeRedrawsTheGlyphs(qtbot, monkeypatch) -> None:
    """The ink has to follow the theme, or it disappears into it."""
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    asked: list[bool] = []
    monkeypatch.setattr(appIcons, "isDarkBackground", lambda: asked.append(True) or True)

    mainWindow.applyActionIcons()
    mainWindow.listsPanel.applyIcons()

    # four menu commands and two buttons, each having asked which ink to use
    assert len(asked) == 6
