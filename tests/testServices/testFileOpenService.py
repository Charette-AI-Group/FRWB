"""Tests for handing a file to the system's default application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl

from frwb.services import fileOpenService as service


class StubOpener:
    """Stands in for the shell, recording what it was asked to open."""

    def __init__(self, answer: bool = True) -> None:
        self.answer = answer
        self.urls: list[str] = []

    def __call__(self, url: QUrl) -> bool:
        self.urls.append(url.toString())
        return self.answer


def testAnExistingFileIsHandedToTheShell(tmp_path) -> None:
    path = tmp_path / "photo.jpg"
    path.write_bytes(b"x")
    opener = StubOpener()

    problem = service.openFile(path, opener)

    assert problem == ""
    assert len(opener.urls) == 1
    assert opener.urls[0].startswith("file:")
    assert opener.urls[0].endswith("photo.jpg")


def testAFileThatIsGoneSaysSoAndIsNotOpened(tmp_path) -> None:
    opener = StubOpener()

    problem = service.openFile(tmp_path / "gone.jpg", opener)

    assert "no longer on the disk" in problem
    assert "gone.jpg" in problem
    assert opener.urls == [], "nothing is handed to the shell"


def testARefusalIsReportedWithThePath(tmp_path) -> None:
    path = tmp_path / "mystery.zzz"
    path.write_bytes(b"x")

    problem = service.openFile(path, StubOpener(answer=False))

    assert "would not open" in problem
    assert str(path) in problem


def testTheRealOpenerIsUsedByDefault(tmp_path, monkeypatch) -> None:
    """Without an opener it goes to QDesktopServices, not to nothing."""
    path = tmp_path / "photo.jpg"
    path.write_bytes(b"x")
    asked: list[str] = []
    monkeypatch.setattr(
        "frwb.services.fileOpenService.QDesktopServices.openUrl",
        lambda url: asked.append(url.toString()) or True,
    )

    assert service.openFile(path) == ""
    assert asked and asked[0].endswith("photo.jpg")


def testTheMessagesNameTheFile() -> None:
    path = Path("C:/photos/a.jpg")

    assert str(path) in service.missingMessage(path)
    assert str(path) in service.refusedMessage(path)
