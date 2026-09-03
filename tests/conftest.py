"""Shared pytest configuration."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from frwb import appConfig
from frwb.models.renameModels import FileEntry


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolatedSettings(tmp_path, monkeypatch):
    """Keep tests out of the real %APPDATA% settings and undo log."""
    monkeypatch.setattr(appConfig, "settingsFile", tmp_path / "settings.ini")
    monkeypatch.setattr(appConfig, "undoLogFile", tmp_path / "lastRename.json")


@pytest.fixture(autouse=True)
def restoreColorScheme(qapp):
    """A forced colour scheme is global; put it back after every test."""
    yield
    qapp.styleHints().unsetColorScheme()


@pytest.fixture
def observableColorScheme(qapp) -> bool:
    """Whether this platform plugin reports a forced colour scheme back.

    The offscreen plugin accepts setColorScheme and then still answers
    Unknown, so tests that want to observe the result skip when this is False.
    """
    hints = qapp.styleHints()
    hints.setColorScheme(Qt.ColorScheme.Dark)
    supported = hints.colorScheme() == Qt.ColorScheme.Dark
    hints.unsetColorScheme()
    return supported


def makeEntry(
    name: str,
    folder: Path | str = "C:/photos",
    created: datetime.datetime | None = None,
    modified: datetime.datetime | None = None,
    taken: datetime.datetime | None = None,
) -> FileEntry:
    """An entry with fixed dates, so names built from them are predictable."""
    return FileEntry(
        path=Path(folder) / name,
        createdAt=created or datetime.datetime(2024, 1, 2, 3, 4, 5),
        modifiedAt=modified or datetime.datetime(2025, 6, 7, 8, 9, 10),
        takenAt=taken,
        sizeBytes=123,
    )
