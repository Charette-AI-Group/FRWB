"""Background thread for reading a folder.

A folder of photos means opening every file for its EXIF date, which is
exactly the kind of wait the interface thread must not take.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from frwb.services import fileScanService

logger = logging.getLogger(__name__)


class FileScanWorker(QThread):
    # The list[FileEntry] found, or why the folder could not be read.
    scanned = Signal(object)
    failed = Signal(str)

    def __init__(self, folder: Path, parent: object | None = None) -> None:
        super().__init__(parent)
        self.folder = folder

    def run(self) -> None:
        try:
            entries = fileScanService.scanFolder(self.folder)
        except OSError as exc:
            logger.warning("Could not read %s: %s", self.folder, exc)
            self.failed.emit(f"Could not read the folder.\n\n{self.folder}\n\n{exc}")
            return
        self.scanned.emit(entries)
