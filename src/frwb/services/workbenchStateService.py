"""Remembering the folder and the rename settings between sessions."""

from __future__ import annotations

import datetime
from enum import StrEnum

from PySide6.QtCore import QSettings

from frwb.models.renameModels import (
    CaseMode,
    DateSource,
    NumberMode,
    NumberPosition,
    RenameSettings,
    SortKey,
    WorkbenchState,
)
from frwb.services import settingsService


def enumOr[EnumType: StrEnum](kind: type[EnumType], value: object, default: EnumType) -> EnumType:
    try:
        return kind(str(value))
    except ValueError:
        return default


def intOr(value: object, default: int) -> int:
    try:
        return int(str(value))
    except ValueError:
        return default


def dateOr(value: object) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def loadRenameSettings(store: QSettings) -> RenameSettings:
    default = RenameSettings()
    return RenameSettings(
        pattern=str(store.value("rename/pattern", default.pattern)),
        numberMode=enumOr(NumberMode, store.value("rename/numberMode"), default.numberMode),
        numberPosition=enumOr(
            NumberPosition, store.value("rename/numberPosition"), default.numberPosition
        ),
        counterStart=intOr(store.value("rename/counterStart"), default.counterStart),
        counterStep=intOr(store.value("rename/counterStep"), default.counterStep),
        counterDigits=intOr(store.value("rename/counterDigits"), default.counterDigits),
        dateSource=enumOr(DateSource, store.value("rename/dateSource"), default.dateSource),
        dateFormat=str(store.value("rename/dateFormat", default.dateFormat)),
        customDate=dateOr(store.value("rename/customDate", "")),
        findText=str(store.value("rename/findText", "")),
        replaceText=str(store.value("rename/replaceText", "")),
        nameCase=enumOr(CaseMode, store.value("rename/nameCase"), default.nameCase),
        extensionCase=enumOr(
            CaseMode, store.value("rename/extensionCase"), default.extensionCase
        ),
    )


def loadState() -> WorkbenchState:
    store = settingsService.openSettings()
    default = WorkbenchState()
    return WorkbenchState(
        folder=str(store.value("workbench/folder", default.folder)),
        fileFilter=str(store.value("workbench/fileFilter", default.fileFilter)),
        sortKey=enumOr(SortKey, store.value("workbench/sortKey"), default.sortKey),
        settings=loadRenameSettings(store),
    )


def saveState(state: WorkbenchState) -> None:
    rename = state.settings
    customDate = rename.customDate.isoformat() if rename.customDate else ""
    settingsService.writeValues(
        {
            "workbench/folder": state.folder,
            "workbench/fileFilter": state.fileFilter,
            "workbench/sortKey": state.sortKey.value,
            "rename/pattern": rename.pattern,
            "rename/numberMode": rename.numberMode.value,
            "rename/numberPosition": rename.numberPosition.value,
            "rename/counterStart": rename.counterStart,
            "rename/counterStep": rename.counterStep,
            "rename/counterDigits": rename.counterDigits,
            "rename/dateSource": rename.dateSource.value,
            "rename/dateFormat": rename.dateFormat,
            "rename/customDate": customDate,
            "rename/findText": rename.findText,
            "rename/replaceText": rename.replaceText,
            "rename/nameCase": rename.nameCase.value,
            "rename/extensionCase": rename.extensionCase.value,
        }
    )
