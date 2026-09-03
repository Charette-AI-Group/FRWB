"""Smoke tests for the controls above the panels."""

from __future__ import annotations

import datetime

from frwb import appConfig
from frwb.models.renameModels import CaseMode, DateSource, NumberMode, RenameSettings
from frwb.ui.widgets.renameControlsPanel import RenameControlsPanel


def ticked(panel: RenameControlsPanel, token: str) -> bool:
    """Whether a token button is wearing the tick rather than the blank."""
    return panel.tokenButtons[token].icon().cacheKey() == panel.checkIcon.cacheKey()


def testTheNameControlsSitInTwoGroups(qtbot) -> None:
    """The template and the changes made to the text are separate jobs."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    assert panel.patternGroup.title() == "Name Pattern"
    assert panel.modifierGroup.title() == "Name Modifiers"

    for widget in (panel.patternEdit, panel.presetsButton):
        assert widget.parent() is panel.patternGroup
    for widget in (
        panel.findEdit,
        panel.replaceEdit,
        panel.nameCaseCombo,
        panel.extensionCaseCombo,
    ):
        assert widget.parent() is panel.modifierGroup


def testDefaultsMatchTheModel(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    settings = panel.currentSettings()
    expected = RenameSettings(customDate=settings.customDate)

    assert settings == expected
    assert settings.pattern == appConfig.defaultPattern
    assert not panel.customDateEdit.isEnabled()


def testApplyAndReadBackRoundTrip(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    wanted = RenameSettings(
        pattern="{date}_{n}",
        numberMode=NumberMode.counter,
        counterStart=5,
        counterStep=2,
        counterDigits=4,
        dateSource=DateSource.custom,
        dateFormat="%Y-%m-%d",
        customDate=datetime.datetime(2021, 3, 4, 5, 6, 7),
        findText="a",
        replaceText="b",
        nameCase=CaseMode.title,
        extensionCase=CaseMode.lower,
    )

    with qtbot.waitSignal(panel.settingsChanged, timeout=1000):
        panel.applySettings(wanted)

    assert panel.currentSettings() == wanted
    assert panel.customDateEdit.isEnabled()


def pickNumberMode(panel: RenameControlsPanel, mode: NumberMode) -> None:
    panel.numberModeCombo.setCurrentIndex(panel.numberModeCombo.findData(mode))


def testTheCounterIsGreyedOutWhenNothingWouldUseIt(qtbot) -> None:
    """The default pattern is {name}: no counter reaches the new names."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    assert not panel.counterGroup.isEnabled()
    assert "{n}" in panel.counterHintLabel.text()


def testTypingTheCounterTokenTurnsTheCounterOn(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.patternEdit.setText("{name}_{n}")
    assert panel.counterGroup.isEnabled()

    panel.patternEdit.setText("{name}")
    assert not panel.counterGroup.isEnabled()


def testInsertingTheTokenFromTheMenuTurnsItOnToo(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.insertToken("n")

    assert panel.counterGroup.isEnabled()


def testReplaceWithCounterTurnsItOnWithoutTheToken(qtbot) -> None:
    """Greying on the token alone would switch it off under a working batch."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    assert panel.patternEdit.text() == "{name}"

    pickNumberMode(panel, NumberMode.counter)

    assert panel.counterGroup.isEnabled()


def testTheNameTokenAloneDoesNotTurnItOn(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.patternEdit.setText("{name}_{date}")

    assert not panel.counterGroup.isEnabled()


def testLoadedSettingsSetTheCounterAvailability(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.applySettings(RenameSettings(pattern="{date}_{n}"))
    assert panel.counterGroup.isEnabled()

    panel.applySettings(RenameSettings(pattern="{date}"))
    assert not panel.counterGroup.isEnabled()


def sourceRowIsLive(panel: RenameControlsPanel) -> bool:
    label = panel.dateForm.labelForField(panel.dateSourceCombo)
    return panel.dateSourceCombo.isEnabled() and label.isEnabled()


def testTheDateGroupIsGreyedOutWhenNoDateReachesTheName(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    assert not panel.dateGroup.isEnabled()
    assert "{date}" in panel.dateHintLabel.text()


def testTheDateTokenTurnsTheWholeGroupOn(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.patternEdit.setText("{date}_{name}")

    assert panel.dateGroup.isEnabled()
    assert sourceRowIsLive(panel)
    assert panel.dateFormatCombo.isEnabled()


def testACreatedTokenLeavesTheFormatLiveAndTheSourceGreyed(qtbot) -> None:
    """The reason the group is not one switch: {created} names its own source."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.patternEdit.setText("{created}_{name}")

    assert panel.dateGroup.isEnabled()
    assert panel.dateFormatCombo.isEnabled()
    assert not sourceRowIsLive(panel)
    assert not panel.customDateEdit.isEnabled()


def testReplaceWithDateTurnsTheSourceOnWithoutAToken(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    assert panel.patternEdit.text() == "{name}"

    pickNumberMode(panel, NumberMode.date)

    assert panel.dateGroup.isEnabled()
    assert sourceRowIsLive(panel)


def testCustomNeedsBothAUsedSourceAndTheCustomChoice(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    customIndex = panel.dateSourceCombo.findData(DateSource.custom)

    # chosen, but nothing in the name uses the date
    panel.dateSourceCombo.setCurrentIndex(customIndex)
    assert not panel.customDateEdit.isEnabled()

    # now the date is used, so the choice has something to do
    panel.patternEdit.setText("{date}")
    assert panel.customDateEdit.isEnabled()

    # used, but the source is a file date again
    panel.dateSourceCombo.setCurrentIndex(panel.dateSourceCombo.findData(DateSource.created))
    assert not panel.customDateEdit.isEnabled()


def testTheCounterStepSkipsZero(qtbot) -> None:
    """A step of zero gives every file the same number, so it is not offered."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.counterStepSpin.stepDown()

    assert panel.counterStepSpin.value() == -1
    assert panel.currentSettings().counterStep == -1


def testAStoredCounterStepOfZeroIsCorrectedOnLoad(qtbot) -> None:
    """Settings written before the rule existed must not bring zero back."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.applySettings(RenameSettings(counterStep=0))

    assert panel.currentSettings().counterStep == 1


def testEditingThePatternAnnouncesAChange(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.settingsChanged, timeout=1000):
        panel.patternEdit.setText("{name}_{n}")

    assert panel.currentSettings().pattern == "{name}_{n}"


def testInsertTokenGoesAtTheCursor(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    panel.patternEdit.setText("ab")
    panel.patternEdit.setCursorPosition(1)

    panel.insertToken("n")

    assert panel.patternEdit.text() == "a{n}b"


def testEveryTokenHasAButtonOfItsOwn(qtbot) -> None:
    """Out in the open, so a new user sees all eight without opening a menu."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    expected = [token for token, _ in appConfig.patternTokens]

    assert list(panel.tokenButtons) == expected
    for token, button in panel.tokenButtons.items():
        assert button.text() == f"{{{token}}}"
        assert button.parent() is panel.patternGroup


def testClickingATokenButtonInsertsItAtTheCursor(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    panel.patternEdit.setText("ab")
    panel.patternEdit.setCursorPosition(1)

    panel.tokenButtons["n"].click()

    assert panel.patternEdit.text() == "a{n}b"


def testClickingTwiceInsertsTwice(qtbot) -> None:
    """The button inserts; it does not toggle, so a token can repeat."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    panel.patternEdit.clear()

    panel.tokenButtons["n"].click()
    panel.tokenButtons["n"].click()

    assert panel.patternEdit.text() == "{n}{n}"


def testTheTicksFollowThePattern(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    panel.patternEdit.setText("{date}_{name}")

    assert not panel.tokenButtons["date"].icon().isNull()
    assert not panel.tokenButtons["name"].icon().isNull()
    assert ticked(panel, "date") and ticked(panel, "name")
    assert not ticked(panel, "n")

    panel.patternEdit.setText("{n}")

    assert ticked(panel, "n")
    assert not ticked(panel, "date")


def testTheBlankHoldsTheTicksPlace(qtbot) -> None:
    """An unticked button must be the same size as a ticked one."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.patternEdit.clear()
    unticked = panel.tokenButtons["name"].sizeHint()

    panel.patternEdit.setText("{name}")

    assert ticked(panel, "name")
    assert panel.tokenButtons["name"].sizeHint() == unticked


def testThePresetsPopupStillOffersEveryPreset(qtbot) -> None:
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)

    presetActions = panel.presetsButton.menu().actions()

    assert len(presetActions) == len(appConfig.patternPresets)


def testAPresetSetsThePatternAndTheTicksFollow(qtbot) -> None:
    """What the preset chose has to show up on the buttons by itself."""
    panel = RenameControlsPanel()
    qtbot.addWidget(panel)
    label, pattern = appConfig.patternPresets[1]
    assert pattern == "{name}_{n}", label

    panel.presetsButton.menu().actions()[1].trigger()

    assert panel.patternEdit.text() == pattern
    assert ticked(panel, "name") and ticked(panel, "n")
    assert not ticked(panel, "date")
