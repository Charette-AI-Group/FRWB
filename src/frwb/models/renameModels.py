"""Plain data for the rename workbench. No Qt, no I/O."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class NumberMode(StrEnum):
    """What to do with a number found in the original name."""

    keep = "keep"
    counter = "counter"
    date = "date"
    remove = "remove"


class NumberPosition(StrEnum):
    """Which number, when a name holds more than one."""

    last = "last"
    first = "first"


class DateSource(StrEnum):
    created = "created"
    modified = "modified"
    taken = "taken"
    custom = "custom"


class CaseMode(StrEnum):
    keep = "keep"
    lower = "lower"
    upper = "upper"
    title = "title"


class SortKey(StrEnum):
    """The order of the list, which is also the order the counter runs in."""

    name = "name"
    created = "created"
    modified = "modified"
    taken = "taken"


@dataclass(frozen=True)
class FileEntry:
    path: Path
    createdAt: datetime.datetime
    modifiedAt: datetime.datetime
    takenAt: datetime.datetime | None = None
    sizeBytes: int = 0

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def suffix(self) -> str:
        return self.path.suffix


@dataclass
class RenameSettings:
    """Everything the controls panel says about how names are built."""

    pattern: str = "{name}"
    numberMode: NumberMode = NumberMode.keep
    numberPosition: NumberPosition = NumberPosition.last
    counterStart: int = 1
    counterStep: int = 1
    counterDigits: int = 3
    dateSource: DateSource = DateSource.created
    dateFormat: str = "%Y%m%d_%H%M%S"
    customDate: datetime.datetime | None = None
    findText: str = ""
    replaceText: str = ""
    nameCase: CaseMode = CaseMode.keep
    extensionCase: CaseMode = CaseMode.keep


@dataclass
class WorkbenchState:
    """What is remembered between sessions."""

    folder: str = ""
    fileFilter: str = "*"
    sortKey: SortKey = SortKey.name
    settings: RenameSettings = field(default_factory=RenameSettings)


class PreviewStatus(StrEnum):
    renamed = "renamed"
    unchanged = "unchanged"
    skipped = "skipped"
    conflict = "conflict"
    invalid = "invalid"


@dataclass(frozen=True)
class RenamePreview:
    source: Path
    newName: str
    status: PreviewStatus
    note: str = ""

    @property
    def target(self) -> Path:
        return self.source.with_name(self.newName)


@dataclass(frozen=True)
class RenameOperation:
    source: Path
    target: Path


@dataclass
class RenameResult:
    applied: list[RenameOperation] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
