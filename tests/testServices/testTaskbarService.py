"""Tests for the Windows taskbar identity."""

from __future__ import annotations

import sys

from frwb import appConfig
from frwb.services import taskbarService as service


def testTheIdentityNamesTheVendorAndTheApplication() -> None:
    identity = service.taskbarIdentity()

    assert identity == f"{appConfig.organizationName}.{appConfig.appShortName}"
    assert "." in identity, "Windows expects a dotted identifier"


def testItIsAppliedOnWindowsAndSkippedElsewhere() -> None:
    applied = service.applyTaskbarIdentity()

    assert applied == (sys.platform == "win32")


def testAPlatformWithoutTheCallIsNotAFailure(monkeypatch) -> None:
    """A Windows that refuses costs the taskbar icon, not the launch."""
    monkeypatch.setattr(service.sys, "platform", "linux")

    assert service.applyTaskbarIdentity() is False
