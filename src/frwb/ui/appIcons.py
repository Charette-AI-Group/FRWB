"""The application icon and the command glyphs, loaded in one place.

Which glyph to use depends on what it will sit on, and this app lets the
user change that under Help > Theme. Asking Qt for the window colour rather
than for the chosen theme answers for all three cases at once, including
"follow Windows", where the app never learns what was chosen.

A missing file gives an empty QIcon rather than an error: the application
runs with text-only menus instead of failing, which is the same contract
``appConfig.iconFile`` has.
"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication, QIcon, QPalette

from frwb import appConfig


def isDarkBackground() -> bool:
    """Whether widgets are being painted on a dark ground right now.

    From the palette, not from the saved theme: with the theme set to follow
    Windows the saved value says nothing about which way Windows went.
    """
    window = QGuiApplication.palette().color(QPalette.ColorRole.Window)
    return window.lightness() < 128


def applicationIcon() -> QIcon:
    path = appConfig.iconFile()
    return QIcon(str(path)) if path is not None else QIcon()


def actionIconOn(key: str, onDark: bool) -> QIcon:
    """The glyph for one command, in the ink a named ground needs.

    For a widget that paints a ground of its own, which can be the opposite
    lightness of the window it sits in.
    """
    path = appConfig.actionIconFile(key, onDark)
    return QIcon(str(path)) if path is not None else QIcon()


def actionIcon(key: str) -> QIcon:
    """The glyph for one command, in the ink this theme needs."""
    return actionIconOn(key, isDarkBackground())
