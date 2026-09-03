"""Background thread for applying a batch of renames."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from frwb.models.renameModels import RenameOperation
from frwb.services import renameExecuteService


class RenameWorker(QThread):
    # The RenameResult: what was applied and what was not.
    completed = Signal(object)

    def __init__(self, operations: list[RenameOperation], parent: object | None = None) -> None:
        super().__init__(parent)
        self.operations = operations

    def run(self) -> None:
        self.completed.emit(renameExecuteService.executeRenames(self.operations))
