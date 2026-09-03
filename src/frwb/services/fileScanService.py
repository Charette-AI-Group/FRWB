"""Listing the files of a folder, and ordering them.

Scanning reads every file's dates once, including the EXIF date of photos,
so that changing the filter or the sort order afterwards costs nothing.
"""

from __future__ import annotations

import datetime
import fnmatch
import os
import re
from pathlib import Path

from frwb.models.renameModels import FileEntry, SortKey
from frwb.services import exifService

filterSeparator = ";"
digitRun = re.compile(r"(\d+)")


def scanFolder(folder: Path) -> list[FileEntry]:
    """Every file directly in the folder. Raises OSError if it cannot be read."""
    entries: list[FileEntry] = []
    with os.scandir(folder) as items:
        for item in items:
            if not item.is_file():
                continue
            entries.append(entryFor(Path(item.path), item.stat()))
    return entries


def entryFor(path: Path, stat: os.stat_result) -> FileEntry:
    # st_birthtime is the creation time where the platform has one (Windows,
    # macOS); st_ctime is the nearest thing elsewhere.
    created = getattr(stat, "st_birthtime", None) or stat.st_ctime
    return FileEntry(
        path=path,
        createdAt=datetime.datetime.fromtimestamp(created),
        modifiedAt=datetime.datetime.fromtimestamp(stat.st_mtime),
        takenAt=exifService.readTakenAt(path),
        sizeBytes=stat.st_size,
    )


def filterPatterns(filterText: str) -> list[str]:
    """'*.jpg; *.png' -> ['*.jpg', '*.png']; blank means everything."""
    patterns = [part.strip() for part in filterText.split(filterSeparator)]
    return [pattern for pattern in patterns if pattern] or ["*"]


def filterEntries(entries: list[FileEntry], filterText: str) -> list[FileEntry]:
    """Case-insensitive on every platform, since the names are Windows names."""
    patterns = [pattern.casefold() for pattern in filterPatterns(filterText)]
    return [
        entry
        for entry in entries
        if any(fnmatch.fnmatchcase(entry.name.casefold(), pattern) for pattern in patterns)
    ]


def naturalKey(text: str) -> list[object]:
    """Sorts file2 before file10, the way a person would."""
    return [int(part) if part.isdigit() else part.casefold() for part in digitRun.split(text)]


def sortEntries(entries: list[FileEntry], sortKey: SortKey) -> list[FileEntry]:
    if sortKey == SortKey.created:
        return sorted(entries, key=lambda e: (e.createdAt, naturalKey(e.name)))
    if sortKey == SortKey.modified:
        return sorted(entries, key=lambda e: (e.modifiedAt, naturalKey(e.name)))
    if sortKey == SortKey.taken:
        return sorted(entries, key=lambda e: (e.takenAt or e.modifiedAt, naturalKey(e.name)))
    return sorted(entries, key=lambda e: naturalKey(e.name))
