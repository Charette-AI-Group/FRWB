"""Working out the new names from the settings, without touching the disk.

Each step is a small pure function so that the preview in the window is,
by construction, exactly what the rename will do.
"""

from __future__ import annotations

import datetime
import re
from collections import Counter
from collections.abc import Iterable, Sequence

from frwb.models.renameModels import (
    CaseMode,
    DateSource,
    FileEntry,
    NumberMode,
    NumberPosition,
    PreviewStatus,
    RenamePreview,
    RenameSettings,
)

numberPattern = re.compile(r"\d+")
tokenPattern = re.compile(r"\{(\w+)\}")
illegalCharacters = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
separators = " _-"
reservedNames = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
maxNameLength = 255

noNumberNote = "No number found in the name."
noTakenDateNote = "No photo date in this file, so the modified date was used."
emptyNameNote = "The new name is empty."
tooLongNote = "The new name is too long."
duplicateNote = "Two or more files would get this name."
existingNote = "A file with this name already exists in the folder."
notCheckedNote = "Not checked."


def findNumber(stem: str, position: NumberPosition) -> re.Match[str] | None:
    matches = list(numberPattern.finditer(stem))
    if not matches:
        return None
    return matches[0] if position == NumberPosition.first else matches[-1]


def counterText(index: int, settings: RenameSettings) -> str:
    value = settings.counterStart + index * settings.counterStep
    return f"{value:0{settings.counterDigits}d}"


def formatDate(value: datetime.datetime | None, dateFormat: str) -> str:
    if value is None:
        return ""
    try:
        return value.strftime(dateFormat)
    except ValueError:
        return ""


def dateFor(
    entry: FileEntry, settings: RenameSettings, source: DateSource
) -> tuple[datetime.datetime, str]:
    """The date a source names, and a note when another had to stand in."""
    if source == DateSource.custom:
        return settings.customDate or datetime.datetime.now(), ""
    if source == DateSource.created:
        return entry.createdAt, ""
    if source == DateSource.modified:
        return entry.modifiedAt, ""
    if entry.takenAt is not None:
        return entry.takenAt, ""
    return entry.modifiedAt, noTakenDateNote


def replaceNumber(stem: str, settings: RenameSettings, replacement: str) -> str:
    match = findNumber(stem, settings.numberPosition)
    if match is None:
        return stem
    left, right = stem[: match.start()], stem[match.end() :]
    if replacement == "":
        # IMG_0001 becomes IMG, not IMG_; 0001_IMG becomes IMG, not _IMG.
        left = left.rstrip(separators)
        if not left:
            right = right.lstrip(separators)
    return left + replacement + right


def applyNumberMode(
    stem: str, settings: RenameSettings, counter: str, date: str
) -> tuple[str, str]:
    if settings.numberMode == NumberMode.keep:
        return stem, ""
    if findNumber(stem, settings.numberPosition) is None:
        return stem, noNumberNote
    replacement = {
        NumberMode.counter: counter,
        NumberMode.date: date,
        NumberMode.remove: "",
    }[settings.numberMode]
    return replaceNumber(stem, settings, replacement), ""


def applyCase(text: str, mode: CaseMode) -> str:
    if mode == CaseMode.lower:
        return text.lower()
    if mode == CaseMode.upper:
        return text.upper()
    if mode == CaseMode.title:
        return text.title()
    return text


def expandPattern(pattern: str, values: dict[str, str]) -> str:
    """Unknown tokens are left as typed, so a typo shows up in the preview."""
    return tokenPattern.sub(lambda match: values.get(match.group(1), match.group(0)), pattern)


def patternTokenNames(pattern: str) -> set[str]:
    """The tokens a pattern uses, read the same way expandPattern reads them."""
    return {match.group(1) for match in tokenPattern.finditer(pattern)}


#: The tokens that put a date in a name. {date} takes whichever source the
#: user picks; the other three name their own and only need the format.
dateTokenNames = frozenset({"date", "created", "modified", "taken"})


def usesDate(settings: RenameSettings) -> bool:
    """Whether the *chosen date source* reaches the new names.

    {created}, {modified} and {taken} do not count: each names its own
    source, so what Source picks is only ever used for {date} and for
    replacing a number with the date.
    """
    return settings.numberMode == NumberMode.date or "date" in patternTokenNames(
        settings.pattern
    )


def usesDateFormat(settings: RenameSettings) -> bool:
    """Whether the format string reaches the new names.

    Wider than usesDate, and that difference is the whole reason these two
    exist separately: every date token is printed through the format, so
    {created} alone keeps Format live while leaving Source with nothing to do.
    """
    return usesDate(settings) or bool(dateTokenNames & patternTokenNames(settings.pattern))


def usesCounter(settings: RenameSettings) -> bool:
    """Whether the counter reaches the new names at all.

    Two ways in, and the second is the one that gets forgotten: the {n}
    token, and replacing a number already in the name with the counter.
    Anything asking whether the counter matters has to ask about both, or it
    will switch the counter off under a batch that is using it.
    """
    return settings.numberMode == NumberMode.counter or "n" in patternTokenNames(
        settings.pattern
    )


def sanitizeFileName(name: str) -> str:
    return illegalCharacters.sub("_", name).strip().rstrip(". ")


def tokenValues(
    entry: FileEntry, settings: RenameSettings, stem: str, counter: str, date: str
) -> dict[str, str]:
    dateFormat = settings.dateFormat
    return {
        "name": stem,
        "n": counter,
        "date": date,
        "created": formatDate(entry.createdAt, dateFormat),
        "modified": formatDate(entry.modifiedAt, dateFormat),
        "taken": formatDate(entry.takenAt, dateFormat),
        "parent": entry.path.parent.name,
        "ext": entry.suffix.lstrip("."),
    }


def buildStem(entry: FileEntry, settings: RenameSettings, index: int) -> tuple[str, list[str]]:
    """The new name before its extension, and the notes gathered on the way."""
    counter = counterText(index, settings)
    date, dateNote = dateFor(entry, settings, settings.dateSource)
    dateText = formatDate(date, settings.dateFormat)
    stem, numberNote = applyNumberMode(entry.stem, settings, counter, dateText)
    if settings.findText:
        stem = stem.replace(settings.findText, settings.replaceText)
    values = tokenValues(entry, settings, stem, counter, dateText)
    newStem = applyCase(expandPattern(settings.pattern, values), settings.nameCase)

    notes: list[str] = []
    if numberNote:
        notes.append(numberNote)
    if dateNote and usesDate(settings):
        notes.append(dateNote)
    if "taken" in patternTokenNames(settings.pattern) and entry.takenAt is None:
        notes.append(noTakenDateNote)
    return sanitizeFileName(newStem), notes


def validationNote(stem: str, name: str) -> str:
    if not stem:
        return emptyNameNote
    if stem.upper() in reservedNames:
        return f"{stem.upper()} is a name Windows reserves."
    if len(name) > maxNameLength:
        return tooLongNote
    return ""


def previewFor(entry: FileEntry, settings: RenameSettings, index: int) -> RenamePreview:
    """One file's preview, before conflicts with the others are known."""
    stem, notes = buildStem(entry, settings, index)
    name = sanitizeFileName(stem + applyCase(entry.suffix, settings.extensionCase))
    invalid = validationNote(stem, name)
    if invalid:
        return RenamePreview(entry.path, name, PreviewStatus.invalid, invalid)
    status = PreviewStatus.unchanged if name == entry.name else PreviewStatus.renamed
    return RenamePreview(entry.path, name, status, " ".join(notes))


def buildPreviews(
    entries: Sequence[FileEntry],
    settings: RenameSettings,
    existingNames: Iterable[str] = (),
    included: Sequence[bool] | None = None,
) -> list[RenamePreview]:
    """Previews for the batch, in order, with conflicts between them marked.

    existingNames are every file in the folder, including the ones the filter
    hides: a new name must not land on any of them. Unchecked entries keep
    their names and do not use up a counter value.
    """
    flags = list(included) if included is not None else [True] * len(entries)
    previews: list[RenamePreview] = []
    counterIndex = 0
    for entry, isIncluded in zip(entries, flags, strict=True):
        if not isIncluded:
            previews.append(
                RenamePreview(entry.path, entry.name, PreviewStatus.skipped, notCheckedNote)
            )
            continue
        previews.append(previewFor(entry, settings, counterIndex))
        counterIndex += 1
    return markConflicts(previews, existingNames)


def markConflicts(
    previews: list[RenamePreview], existingNames: Iterable[str]
) -> list[RenamePreview]:
    """Two files landing on one name, or on a name that is staying put.

    Names are compared case-insensitively, as Windows does. Two files
    swapping names is not a conflict: the rename service handles that.
    """
    sourceKeys = {p.source.name.casefold() for p in previews}
    keptKeys = {p.source.name.casefold() for p in previews if p.status != PreviewStatus.renamed}
    outsideKeys = {name.casefold() for name in existingNames} - sourceKeys
    counts = Counter(p.newName.casefold() for p in previews if p.status == PreviewStatus.renamed)

    result: list[RenamePreview] = []
    for preview in previews:
        if preview.status != PreviewStatus.renamed:
            result.append(preview)
            continue
        key = preview.newName.casefold()
        if counts[key] > 1:
            note = duplicateNote
        elif key in keptKeys or key in outsideKeys:
            note = existingNote
        else:
            result.append(preview)
            continue
        result.append(RenamePreview(preview.source, preview.newName, PreviewStatus.conflict, note))
    return result


def countByStatus(previews: Iterable[RenamePreview]) -> dict[PreviewStatus, int]:
    counts = Counter(preview.status for preview in previews)
    return {status: counts.get(status, 0) for status in PreviewStatus}
