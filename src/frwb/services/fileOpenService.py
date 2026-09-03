"""Opening a file with whatever application the system has for its extension.

The same thing a double-click in File Explorer does: hand the path to the
shell and let it decide. Windows shows its own "How do you want to open this
file?" chooser when nothing is registered, so that case needs no handling
here - only a file that has since gone, and a shell that refused outright.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)


def missingMessage(path: Path) -> str:
    return (
        f"This file is no longer on the disk.\n\n{path}\n\n"
        "It was moved, renamed or deleted since the list was read. "
        "Press F5 to read the folder again."
    )


def refusedMessage(path: Path) -> str:
    return (
        f"Windows would not open this file.\n\n{path}\n\n"
        "There may be no application registered for this kind of file."
    )


def openFile(path: Path, opener: Callable[[QUrl], bool] | None = None) -> str:
    """Open the file; return an empty string, or why it could not be opened.

    A message rather than a raised error: nothing here is exceptional, and the
    caller has to say the same two things either way.
    """
    launch = opener or QDesktopServices.openUrl
    if not path.exists():
        logger.info("Asked to open a file that is gone: %s", path)
        return missingMessage(path)
    if not launch(QUrl.fromLocalFile(str(path))):
        logger.warning("The shell refused to open %s", path)
        return refusedMessage(path)
    return ""
