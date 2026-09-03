"""Tests for listing, filtering and ordering the files of a folder."""

from __future__ import annotations

import datetime

from conftest import makeEntry

from frwb.models.renameModels import SortKey
from frwb.services import fileScanService as service


def testScanListsFilesButNotFolders(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.jpg").write_bytes(b"not a jpeg")
    (tmp_path / "sub").mkdir()

    entries = service.scanFolder(tmp_path)

    assert sorted(entry.name for entry in entries) == ["a.txt", "b.jpg"]
    assert all(entry.takenAt is None for entry in entries)
    assert all(entry.sizeBytes > 0 for entry in entries)


def testScanRaisesForAMissingFolder(tmp_path) -> None:
    try:
        service.scanFolder(tmp_path / "gone")
    except OSError:
        return
    raise AssertionError("a missing folder must raise, so the window can say so")


def testFilterIsCaseInsensitiveAndTakesSeveralPatterns() -> None:
    entries = [makeEntry("a.JPG"), makeEntry("b.png"), makeEntry("c.txt")]

    kept = service.filterEntries(entries, "*.jpg; *.PNG")

    assert [entry.name for entry in kept] == ["a.JPG", "b.png"]


def testABlankFilterKeepsEverything() -> None:
    entries = [makeEntry("a.JPG"), makeEntry("b.png")]

    assert service.filterEntries(entries, "  ") == entries
    assert service.filterPatterns("") == ["*"]


def testNaturalOrderPutsFile2BeforeFile10() -> None:
    entries = [makeEntry("file10.txt"), makeEntry("file2.txt"), makeEntry("File1.txt")]

    ordered = service.sortEntries(entries, SortKey.name)

    assert [entry.name for entry in ordered] == ["File1.txt", "file2.txt", "file10.txt"]


def testSortByCreatedDate() -> None:
    older = makeEntry("z.txt", created=datetime.datetime(2020, 1, 1))
    newer = makeEntry("a.txt", created=datetime.datetime(2021, 1, 1))

    ordered = service.sortEntries([newer, older], SortKey.created)

    assert [entry.name for entry in ordered] == ["z.txt", "a.txt"]


def testSortByPhotoDateFallsBackToModified() -> None:
    shot = makeEntry("shot.jpg", taken=datetime.datetime(2019, 1, 1))
    plain = makeEntry("plain.txt", modified=datetime.datetime(2018, 1, 1))

    ordered = service.sortEntries([shot, plain], SortKey.taken)

    assert [entry.name for entry in ordered] == ["plain.txt", "shot.jpg"]
