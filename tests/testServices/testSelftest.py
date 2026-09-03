"""Tests for the check that decides whether a build is shippable.

This one gates a release, so it has to fail when something is genuinely
missing. A self-test that passes unconditionally is worse than none: it turns
a broken build into a signed-off one.
"""

from __future__ import annotations

from frwb import appConfig, selftest


def testEveryBundledFileIsChecked(qapp) -> None:
    names = [name for name, _, _ in selftest.resourceChecks()]

    assert "applicationIcon" in names
    assert "manual" in names
    for key in appConfig.actionIconKeys:
        assert f"icon.{key}-onLight" in names
        assert f"icon.{key}-onDark" in names
    # one application icon, one manual, and both inks of every command glyph
    assert len(names) == 2 + 2 * len(appConfig.actionIconKeys)


def testAChekoutPassesItsOwnCheck(qapp) -> None:
    assert all(found for _, found, _ in selftest.resourceChecks())


def testAMissingResourceIsCaught(qapp, monkeypatch, tmp_path) -> None:
    """The failure this exists for: packaging dropped the icons."""
    monkeypatch.setattr(appConfig, "resourcesDir", tmp_path)

    failures = [name for name, found, _ in selftest.resourceChecks() if not found]

    assert "applicationIcon" in failures
    assert f"icon.{appConfig.actionIconKeys[0]}-onLight" in failures


def testAMissingManualIsCaught(qapp, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(appConfig, "manualPath", tmp_path / "gone.md")

    failures = [name for name, found, _ in selftest.resourceChecks() if not found]

    assert failures == ["manual"]


def testTheWindowIsBuiltAndWearsItsIcon(qapp) -> None:
    ok, detail = selftest.windowCheck()

    assert ok, detail
    assert detail == appConfig.windowTitle


def testTheReportNamesTheVersionAndPasses(qapp) -> None:
    text, passed = selftest.report()

    assert passed
    assert f"app={appConfig.appShortName} {appConfig.appVersion}" in text
    assert "result=ok" in text
    assert "MISSING" not in text


def testAFailedCheckShowsUpInTheReportAndTheExitCode(qapp, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(appConfig, "resourcesDir", tmp_path)

    text, passed = selftest.report()

    assert not passed
    assert "MISSING" in text
    assert "result=FAILED" in text
    assert selftest.runSelfTest(str(tmp_path / "report.txt")) == 1


def testTheReportIsWrittenWhereItIsAsked(qapp, tmp_path) -> None:
    """A windowed build has no console, so the file is the whole output."""
    target = tmp_path / "selftest.txt"

    code = selftest.runSelfTest(str(target))

    assert code == 0
    assert "result=ok" in target.read_text(encoding="utf-8")
