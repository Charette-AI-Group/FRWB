"""Tests for remembering the workbench between sessions."""

from __future__ import annotations

import datetime

from frwb.models.renameModels import (
    CaseMode,
    DateSource,
    NumberMode,
    RenameSettings,
    SortKey,
    WorkbenchState,
)
from frwb.services import settingsService
from frwb.services import workbenchStateService as service


def testDefaultsWhenNothingIsSaved(qapp) -> None:
    state = service.loadState()

    assert state == WorkbenchState()


def testRoundTrip(qapp) -> None:
    saved = WorkbenchState(
        folder="C:/photos",
        fileFilter="*.jpg",
        sortKey=SortKey.taken,
        settings=RenameSettings(
            pattern="{date}_{n}",
            numberMode=NumberMode.date,
            counterStart=7,
            counterStep=2,
            counterDigits=4,
            dateSource=DateSource.custom,
            dateFormat="%Y",
            customDate=datetime.datetime(2020, 2, 3, 4, 5, 6),
            findText="IMG",
            replaceText="Trip",
            nameCase=CaseMode.lower,
            extensionCase=CaseMode.upper,
        ),
    )

    service.saveState(saved)

    assert service.loadState() == saved


def testGarbageInTheFileFallsBackToDefaults(qapp) -> None:
    settingsService.writeValues(
        {"rename/numberMode": "banana", "rename/counterStart": "lots", "rename/customDate": "x"}
    )

    settings = service.loadState().settings

    assert settings.numberMode == NumberMode.keep
    assert settings.counterStart == 1
    assert settings.customDate is None
