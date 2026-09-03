"""Tests for applying renames to the disk and undoing them."""

from __future__ import annotations

from pathlib import Path

from frwb.models.renameModels import PreviewStatus, RenameOperation, RenamePreview
from frwb.services import renameExecuteService as service


def op(folder: Path, source: str, target: str) -> RenameOperation:
    return RenameOperation(folder / source, folder / target)


def testOnlyRenamedPreviewsBecomeOperations(tmp_path) -> None:
    previews = [
        RenamePreview(tmp_path / "a.txt", "b.txt", PreviewStatus.renamed),
        RenamePreview(tmp_path / "c.txt", "c.txt", PreviewStatus.unchanged),
        RenamePreview(tmp_path / "d.txt", "e.txt", PreviewStatus.conflict),
    ]

    operations = service.operationsFrom(previews)

    assert operations == [op(tmp_path, "a.txt", "b.txt")]


def testFilesAreRenamed(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("A")

    result = service.executeRenames([op(tmp_path, "a.txt", "b.txt")])

    assert (tmp_path / "b.txt").read_text() == "A"
    assert not (tmp_path / "a.txt").exists()
    assert result.applied == [op(tmp_path, "a.txt", "b.txt")]
    assert result.failed == []


def testSwappingTwoNamesLosesNothing(tmp_path) -> None:
    (tmp_path / "1.txt").write_text("one")
    (tmp_path / "2.txt").write_text("two")

    result = service.executeRenames(
        [op(tmp_path, "1.txt", "2.txt"), op(tmp_path, "2.txt", "1.txt")]
    )

    assert (tmp_path / "1.txt").read_text() == "two"
    assert (tmp_path / "2.txt").read_text() == "one"
    assert len(result.applied) == 2
    assert not list(tmp_path.glob(f"{service.tempPrefix}*"))


def testAFileInTheWayIsReportedAndNothingIsOverwritten(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("A")
    (tmp_path / "b.txt").write_text("B")

    result = service.executeRenames([op(tmp_path, "a.txt", "b.txt")])

    assert (tmp_path / "b.txt").read_text() == "B"
    assert (tmp_path / "a.txt").read_text() == "A", "the source goes back to its own name"
    assert result.applied == []
    assert len(result.failed) == 1 and "a.txt" in result.failed[0]


def testAMissingSourceIsReportedAndTheRestStillHappens(tmp_path) -> None:
    (tmp_path / "b.txt").write_text("B")

    result = service.executeRenames(
        [op(tmp_path, "gone.txt", "x.txt"), op(tmp_path, "b.txt", "c.txt")]
    )

    assert (tmp_path / "c.txt").exists()
    assert len(result.failed) == 1 and "gone.txt" in result.failed[0]


def testUndoLogRoundTripAndReversal(tmp_path) -> None:
    logPath = tmp_path / "log.json"
    operations = [op(tmp_path, "a.txt", "b.txt")]

    service.writeUndoLog(operations, logPath)

    assert service.readUndoLog(logPath) == operations
    assert service.reversedOperations(operations) == [op(tmp_path, "b.txt", "a.txt")]

    service.clearUndoLog(logPath)
    assert service.readUndoLog(logPath) == []
    service.clearUndoLog(logPath)  # a second clear is not an error


def testAGarbledUndoLogReadsAsNothing(tmp_path) -> None:
    logPath = tmp_path / "log.json"
    logPath.write_text("{not json", encoding="utf-8")

    assert service.readUndoLog(logPath) == []
