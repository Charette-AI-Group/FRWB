"""Applying a batch of renames to the disk, and taking it back.

Two phases: every file first moves to a temporary name, then to its final
one. That is what lets a batch swap names or renumber files in place without
one rename overwriting a file the next still needs.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from frwb.models.renameModels import (
    PreviewStatus,
    RenameOperation,
    RenamePreview,
    RenameResult,
)

logger = logging.getLogger(__name__)

tempPrefix = "~frwb-"


def operationsFrom(previews: list[RenamePreview]) -> list[RenameOperation]:
    return [
        RenameOperation(preview.source, preview.target)
        for preview in previews
        if preview.status == PreviewStatus.renamed
    ]


def reversedOperations(operations: list[RenameOperation]) -> list[RenameOperation]:
    return [RenameOperation(op.target, op.source) for op in operations]


def tempNameFor(path: Path) -> Path:
    return path.with_name(f"{tempPrefix}{uuid.uuid4().hex[:8]}-{path.name}")


def executeRenames(operations: list[RenameOperation]) -> RenameResult:
    """Rename every file, reporting each one that could not be.

    Path.rename refuses to overwrite on Windows, which is the safety net: a
    file that is unexpectedly in the way is reported, never replaced.
    """
    result = RenameResult()
    staged: list[tuple[Path, RenameOperation]] = []
    for operation in operations:
        temp = tempNameFor(operation.source)
        try:
            operation.source.rename(temp)
        except OSError as exc:
            result.failed.append(f"{operation.source.name}: {exc.strerror or exc}")
            continue
        staged.append((temp, operation))

    for temp, operation in staged:
        try:
            temp.rename(operation.target)
        except OSError as exc:
            result.failed.append(f"{operation.source.name}: {exc.strerror or exc}")
            restore(temp, operation.source, result)
            continue
        result.applied.append(operation)
    logger.info("Renamed %d files, %d failed", len(result.applied), len(result.failed))
    return result


def restore(temp: Path, source: Path, result: RenameResult) -> None:
    try:
        temp.rename(source)
    except OSError as exc:
        result.failed.append(f"{source.name} is left as {temp.name}: {exc.strerror or exc}")


def writeUndoLog(operations: list[RenameOperation], logPath: Path) -> None:
    logPath.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"source": str(op.source), "target": str(op.target)} for op in operations]
    logPath.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def readUndoLog(logPath: Path) -> list[RenameOperation]:
    """The last batch, or nothing when there is no log or it is unreadable."""
    try:
        payload = json.loads(logPath.read_text(encoding="utf-8"))
        return [RenameOperation(Path(item["source"]), Path(item["target"])) for item in payload]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.info("No usable undo log at %s: %s", logPath, exc)
        return []


def clearUndoLog(logPath: Path) -> None:
    try:
        logPath.unlink()
    except FileNotFoundError:
        pass
