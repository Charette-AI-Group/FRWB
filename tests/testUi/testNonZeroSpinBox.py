"""Tests for the spin box that steps over zero."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QValidator

from frwb.ui.widgets.nonZeroSpinBox import NonZeroSpinBox


@pytest.fixture
def spinBox(qtbot) -> NonZeroSpinBox:
    box = NonZeroSpinBox()
    qtbot.addWidget(box)
    box.setRange(-1000, 1000)
    box.setValue(1)
    return box


def testSteppingDownFromOneReachesMinusOne(spinBox: NonZeroSpinBox) -> None:
    spinBox.stepDown()

    assert spinBox.value() == -1


def testSteppingUpFromMinusOneReachesOne(spinBox: NonZeroSpinBox) -> None:
    spinBox.setValue(-1)

    spinBox.stepUp()

    assert spinBox.value() == 1


def testOrdinaryStepsAreUntouched(spinBox: NonZeroSpinBox) -> None:
    spinBox.setValue(3)
    spinBox.stepDown()
    assert spinBox.value() == 2

    spinBox.setValue(-3)
    spinBox.stepUp()
    assert spinBox.value() == -2


def testAStepThatWouldLandOnZeroCarriesOnPastIt(spinBox: NonZeroSpinBox) -> None:
    """A wheel notch can be worth several steps; zero is skipped either way."""
    spinBox.setValue(-2)

    spinBox.stepBy(2)

    assert spinBox.value() == 1


def testTheEdgesOfTheRangeStillWork(spinBox: NonZeroSpinBox) -> None:
    spinBox.setValue(1000)
    spinBox.stepUp()
    assert spinBox.value() == 1000

    spinBox.setValue(-1000)
    spinBox.stepDown()
    assert spinBox.value() == -1000


def testTypingZeroIsNotAcceptedAsFinished(spinBox: NonZeroSpinBox) -> None:
    """Intermediate, so it can still be typed on the way to another number."""
    state, _, _ = spinBox.validate("0", 1)

    assert state == QValidator.State.Intermediate


def testTypingAnOrdinaryNumberIsAccepted(spinBox: NonZeroSpinBox) -> None:
    for text in ("5", "-5", "12"):
        state, _, _ = spinBox.validate(text, len(text))
        assert state == QValidator.State.Acceptable, text


def testZeroLeftStandingIsCorrectedRatherThanKept(spinBox: NonZeroSpinBox) -> None:
    assert spinBox.fixup("0") == "1"
    assert spinBox.fixup("-0") == "1"
    assert spinBox.fixup("7") == "7"


def testAStoredZeroIsRefusedToo(spinBox: NonZeroSpinBox) -> None:
    """A settings file written before this rule must not put zero back."""
    spinBox.setValue(0)

    assert spinBox.value() == 1


def testTheReplacementIsTheCallersChoice(qtbot) -> None:
    box = NonZeroSpinBox(replacement=-1)
    qtbot.addWidget(box)
    box.setRange(-10, 10)

    box.setValue(0)

    assert box.value() == -1
