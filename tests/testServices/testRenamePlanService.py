"""Tests for how new names are worked out."""

from __future__ import annotations

import datetime

from conftest import makeEntry

from frwb.models.renameModels import (
    CaseMode,
    DateSource,
    NumberMode,
    NumberPosition,
    PreviewStatus,
    RenameSettings,
)
from frwb.services import renamePlanService as service


def names(previews) -> list[str]:
    return [preview.newName for preview in previews]


def statuses(previews) -> list[PreviewStatus]:
    return [preview.status for preview in previews]


# --- the pattern ---------------------------------------------------------------


def testTheDefaultPatternChangesNothing() -> None:
    previews = service.buildPreviews([makeEntry("a.jpg"), makeEntry("b.jpg")], RenameSettings())

    assert names(previews) == ["a.jpg", "b.jpg"]
    assert statuses(previews) == [PreviewStatus.unchanged] * 2


def testCounterIsPaddedAndRunsInListOrder() -> None:
    settings = RenameSettings(pattern="{name}_{n}", counterStart=1, counterDigits=3)

    previews = service.buildPreviews([makeEntry("b.jpg"), makeEntry("a.jpg")], settings)

    assert names(previews) == ["b_001.jpg", "a_002.jpg"]
    assert statuses(previews) == [PreviewStatus.renamed] * 2


def testCounterStartAndStep() -> None:
    settings = RenameSettings(pattern="{n}", counterStart=10, counterStep=5, counterDigits=2)

    previews = service.buildPreviews([makeEntry("a.jpg"), makeEntry("b.jpg")], settings)

    assert names(previews) == ["10.jpg", "15.jpg"]


def testEveryTokenExpands() -> None:
    entry = makeEntry("IMG_7.jpg", taken=datetime.datetime(2023, 12, 25, 10, 30, 0))
    settings = RenameSettings(
        pattern="{name}|{n}|{date}|{created}|{modified}|{taken}|{parent}|{ext}",
        dateFormat="%Y%m%d",
        dateSource=DateSource.taken,
    )

    stem, _ = service.buildStem(entry, settings, 0)

    # The | is illegal in a file name and becomes _ in the sanitised stem.
    assert stem == "IMG_7_001_20231225_20240102_20250607_20231225_photos_jpg"


def testAnUnknownTokenIsLeftAsTyped() -> None:
    previews = service.buildPreviews([makeEntry("a.jpg")], RenameSettings(pattern="{name}{foo}"))

    assert names(previews) == ["a{foo}.jpg"]


# --- the number in the name ----------------------------------------------------


def testNumberReplacedWithCounter() -> None:
    settings = RenameSettings(numberMode=NumberMode.counter, counterStart=1, counterDigits=2)

    entries = [makeEntry("IMG_0042.jpg"), makeEntry("IMG_0099.jpg")]

    previews = service.buildPreviews(entries, settings)

    assert names(previews) == ["IMG_01.jpg", "IMG_02.jpg"]


def testNumberReplacedWithTheCreatedDate() -> None:
    settings = RenameSettings(
        numberMode=NumberMode.date, dateSource=DateSource.created, dateFormat="%Y%m%d_%H%M%S"
    )

    previews = service.buildPreviews([makeEntry("IMG_0042.jpg")], settings)

    assert names(previews) == ["IMG_20240102_030405.jpg"]


def testNumberRemovedTakesItsSeparatorWithIt() -> None:
    settings = RenameSettings(numberMode=NumberMode.remove)
    entries = [makeEntry("IMG_0042.jpg"), makeEntry("0042_IMG.jpg"), makeEntry("a_12_b.jpg")]

    previews = service.buildPreviews(entries, settings)

    assert names(previews) == ["IMG.jpg", "IMG.jpg", "a_b.jpg"]


def testFirstOrLastNumber() -> None:
    entry = makeEntry("2024_pic_07.jpg")
    last = RenameSettings(numberMode=NumberMode.counter, numberPosition=NumberPosition.last)
    first = RenameSettings(numberMode=NumberMode.counter, numberPosition=NumberPosition.first)

    assert names(service.buildPreviews([entry], last)) == ["2024_pic_001.jpg"]
    assert names(service.buildPreviews([entry], first)) == ["001_pic_07.jpg"]


def testANameWithoutANumberSaysSo() -> None:
    previews = service.buildPreviews(
        [makeEntry("holiday.jpg")], RenameSettings(numberMode=NumberMode.counter)
    )

    assert previews[0].status == PreviewStatus.unchanged
    assert previews[0].note == service.noNumberNote


# --- text and case -------------------------------------------------------------


def testFindAndReplace() -> None:
    settings = RenameSettings(findText="IMG", replaceText="Holiday")

    previews = service.buildPreviews([makeEntry("IMG_0042.jpg")], settings)

    assert names(previews) == ["Holiday_0042.jpg"]


def testFindWithEmptyReplaceDeletes() -> None:
    settings = RenameSettings(findText="_copy")

    previews = service.buildPreviews([makeEntry("a_copy.jpg")], settings)

    assert names(previews) == ["a.jpg"]


def testNameAndExtensionCaseAreIndependent() -> None:
    settings = RenameSettings(nameCase=CaseMode.upper, extensionCase=CaseMode.lower)

    previews = service.buildPreviews([makeEntry("Photo.JPG")], settings)

    assert names(previews) == ["PHOTO.jpg"]
    assert statuses(previews) == [PreviewStatus.renamed]


def testTitleCase() -> None:
    previews = service.buildPreviews(
        [makeEntry("my holiday.jpg")], RenameSettings(nameCase=CaseMode.title)
    )

    assert names(previews) == ["My Holiday.jpg"]


# --- dates ---------------------------------------------------------------------


def testPhotoDateFallsBackToModifiedWithANote() -> None:
    settings = RenameSettings(pattern="{date}", dateSource=DateSource.taken, dateFormat="%Y")

    previews = service.buildPreviews([makeEntry("a.jpg")], settings)

    assert names(previews) == ["2025.jpg"]
    assert previews[0].note == service.noTakenDateNote


def testPhotoDateIsUsedWhenThereIsOne() -> None:
    entry = makeEntry("a.jpg", taken=datetime.datetime(2020, 5, 6))
    settings = RenameSettings(pattern="{date}", dateSource=DateSource.taken, dateFormat="%Y-%m-%d")

    previews = service.buildPreviews([entry], settings)

    assert names(previews) == ["2020-05-06.jpg"]
    assert previews[0].note == ""


def testCustomDate() -> None:
    settings = RenameSettings(
        pattern="{date}_{name}",
        dateSource=DateSource.custom,
        customDate=datetime.datetime(1999, 12, 31, 23, 59),
        dateFormat="%Y%m%d-%H%M",
    )

    previews = service.buildPreviews([makeEntry("a.jpg")], settings)

    assert names(previews) == ["19991231-2359_a.jpg"]


def testABrokenDateFormatDoesNotCrash() -> None:
    """The platforms disagree about a lone %, and neither answer is wrong.

    Windows raises on it, glibc hands the % straight back. What matters is
    that a typo in the format box cannot take the app down, and that the
    preview shows whichever the user's machine produces. Asserting the empty
    string here pinned Windows behaviour and failed the macOS build.
    """
    result = service.formatDate(datetime.datetime(2024, 1, 1), "%")

    assert isinstance(result, str)


# --- what cannot be a file name ------------------------------------------------


def testIllegalCharactersBecomeUnderscores() -> None:
    previews = service.buildPreviews([makeEntry("a.txt")], RenameSettings(pattern="{name}:x?"))

    assert names(previews) == ["a_x_.txt"]


def testAnEmptyNameIsInvalid() -> None:
    previews = service.buildPreviews([makeEntry("a.txt")], RenameSettings(pattern=""))

    assert statuses(previews) == [PreviewStatus.invalid]
    assert previews[0].note == service.emptyNameNote


def testAReservedWindowsNameIsInvalid() -> None:
    previews = service.buildPreviews([makeEntry("a.txt")], RenameSettings(pattern="con"))

    assert statuses(previews) == [PreviewStatus.invalid]
    assert "CON" in previews[0].note


# --- conflicts -----------------------------------------------------------------


def testTwoFilesLandingOnOneNameConflict() -> None:
    previews = service.buildPreviews(
        [makeEntry("a.txt"), makeEntry("b.txt")], RenameSettings(pattern="same")
    )

    assert statuses(previews) == [PreviewStatus.conflict] * 2
    assert previews[0].note == service.duplicateNote


def testANameHeldByAFileOutsideTheBatchConflicts() -> None:
    previews = service.buildPreviews(
        [makeEntry("a.txt")], RenameSettings(pattern="B"), existingNames=["b.txt", "a.txt"]
    )

    assert statuses(previews) == [PreviewStatus.conflict]
    assert previews[0].note == service.existingNote


def testANameHeldByAnUnchangedFileConflicts() -> None:
    # The first keeps its name; the second wants it.
    settings = RenameSettings(findText="b", replaceText="a")

    previews = service.buildPreviews([makeEntry("a.txt"), makeEntry("b.txt")], settings)

    assert statuses(previews) == [PreviewStatus.unchanged, PreviewStatus.conflict]


def testSwappingTwoNamesIsAllowed() -> None:
    settings = RenameSettings(pattern="{n}", counterStart=2, counterStep=-1, counterDigits=1)

    previews = service.buildPreviews([makeEntry("1.txt"), makeEntry("2.txt")], settings)

    assert names(previews) == ["2.txt", "1.txt"]
    assert statuses(previews) == [PreviewStatus.renamed] * 2


def testACaseOnlyRenameIsARenameNotAConflict() -> None:
    previews = service.buildPreviews(
        [makeEntry("Photo.JPG")], RenameSettings(nameCase=CaseMode.lower), ["Photo.JPG"]
    )

    assert names(previews) == ["photo.JPG"]
    assert statuses(previews) == [PreviewStatus.renamed]


# --- unchecked files -----------------------------------------------------------


def testAnUncheckedFileKeepsItsNameAndItsCounterValue() -> None:
    settings = RenameSettings(pattern="{n}", counterDigits=1)
    entries = [makeEntry("a.txt"), makeEntry("b.txt"), makeEntry("c.txt")]

    previews = service.buildPreviews(entries, settings, included=[True, False, True])

    assert names(previews) == ["1.txt", "b.txt", "2.txt"]
    assert previews[1].status == PreviewStatus.skipped


def testAnUncheckedFileStillBlocksItsName() -> None:
    settings = RenameSettings(pattern="b")

    previews = service.buildPreviews(
        [makeEntry("a.txt"), makeEntry("b.txt")], settings, included=[True, False]
    )

    assert statuses(previews) == [PreviewStatus.conflict, PreviewStatus.skipped]


# --- whether the counter is used at all ----------------------------------------


def testTheCounterTokenTurnsTheCounterOn() -> None:
    assert service.usesCounter(RenameSettings(pattern="{name}_{n}"))
    assert service.usesCounter(RenameSettings(pattern="{n}"))


def testReplacingANumberWithTheCounterTurnsItOnWithNoToken() -> None:
    """The route that gets forgotten: no {n} anywhere, counter still used."""
    settings = RenameSettings(pattern="{name}", numberMode=NumberMode.counter)

    assert service.usesCounter(settings)
    assert service.buildPreviews([makeEntry("IMG_9.jpg")], settings)[0].newName == "IMG_001.jpg"


def testNothingElseTurnsTheCounterOn() -> None:
    assert not service.usesCounter(RenameSettings(pattern="{name}"))
    assert not service.usesCounter(RenameSettings(pattern="{date}_{parent}"))
    assert not service.usesCounter(RenameSettings(numberMode=NumberMode.date))
    assert not service.usesCounter(RenameSettings(numberMode=NumberMode.remove))


def testTheNameTokenIsNotTheCounterToken() -> None:
    """A substring check would read the n of {name} as the counter."""
    assert not service.usesCounter(RenameSettings(pattern="{name}"))
    assert service.patternTokenNames("{name}_{n}") == {"name", "n"}


# --- whether the date controls are used at all ---------------------------------


def testTheSourceIsUsedByTheDateTokenAndByReplaceWithDate() -> None:
    assert service.usesDate(RenameSettings(pattern="{date}"))
    assert service.usesDate(RenameSettings(pattern="{name}", numberMode=NumberMode.date))


def testTheOtherDateTokensNameTheirOwnSource() -> None:
    """{created} and its kind leave Source nothing to pick, but still print."""
    for pattern in ("{created}", "{modified}", "{taken}"):
        settings = RenameSettings(pattern=pattern)
        assert not service.usesDate(settings), pattern
        assert service.usesDateFormat(settings), pattern


def testTheFormatIsUsedByEveryDateToken() -> None:
    for pattern in ("{date}", "{created}", "{modified}", "{taken}"):
        assert service.usesDateFormat(RenameSettings(pattern=pattern)), pattern
    assert service.usesDateFormat(RenameSettings(numberMode=NumberMode.date))


def testNeitherDateRuleFiresForANameWithNoDateInIt() -> None:
    settings = RenameSettings(pattern="{name}_{n}")

    assert not service.usesDate(settings)
    assert not service.usesDateFormat(settings)


def testTheFormatReallyDoesReachTheOtherDateTokens() -> None:
    """Why Format stays live for {created}: that token is printed through it."""
    entry = makeEntry("a.jpg")

    dashed = RenameSettings(pattern="{created}", dateFormat="%Y-%m-%d")
    yearOnly = RenameSettings(pattern="{created}", dateFormat="%Y")

    full = service.buildPreviews([entry], dashed)
    year = service.buildPreviews([entry], yearOnly)

    assert full[0].newName == "2024-01-02.jpg"
    assert year[0].newName == "2024.jpg"


def testTheSourceReallyDoesNotReachTheOtherDateTokens() -> None:
    """And why Source greys out for them: moving it changes nothing."""
    entry = makeEntry("a.jpg", taken=datetime.datetime(2020, 5, 6))
    asCreated = RenameSettings(pattern="{created}", dateFormat="%Y", dateSource=DateSource.created)
    asTaken = RenameSettings(pattern="{created}", dateFormat="%Y", dateSource=DateSource.taken)

    assert names(service.buildPreviews([entry], asCreated)) == ["2024.jpg"]
    assert names(service.buildPreviews([entry], asTaken)) == ["2024.jpg"]


def testCountByStatusCoversEveryStatus() -> None:
    previews = service.buildPreviews(
        [makeEntry("a.txt"), makeEntry("b.txt")], RenameSettings(pattern="{name}_x"),
        included=[True, False],
    )

    counts = service.countByStatus(previews)

    assert counts[PreviewStatus.renamed] == 1
    assert counts[PreviewStatus.skipped] == 1
    assert counts[PreviewStatus.conflict] == 0
    assert set(counts) == set(PreviewStatus)
