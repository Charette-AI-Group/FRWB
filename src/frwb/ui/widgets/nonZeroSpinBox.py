"""A spin box that steps over zero: 1 to -1, and back.

Some numbers have no useful zero. A counter step of zero hands every file
the same number, which can only produce a batch of identical names - caught
downstream as a conflict, but caught after the reader has typed it, watched
the preview turn red, and worked out why.

Blocking the value is better than reporting it, and blocking it in the
control means the reason lives next to the number rather than in a message
somewhere else.
"""

from __future__ import annotations

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QSpinBox, QWidget

zeroTexts = frozenset({"0", "-0", "+0"})


class NonZeroSpinBox(QSpinBox):
    """A spin box whose value is never zero, by any of the ways in.

    Three doors have to be shut, not one: the arrows and the wheel come
    through ``stepBy``, typed text through ``validate`` and ``fixup``, and a
    stored value through ``setValue``. Shutting only the first leaves a
    settings file able to put zero back.
    """

    def __init__(self, replacement: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        #: what zero becomes when one arrives from somewhere that cannot step
        self.replacement = replacement

    def strippedText(self, text: str) -> str:
        cleaned = text.strip()
        if self.prefix():
            cleaned = cleaned.removeprefix(self.prefix())
        if self.suffix():
            cleaned = cleaned.removesuffix(self.suffix())
        return cleaned.strip()

    def isZeroText(self, text: str) -> bool:
        return self.strippedText(text) in zeroTexts

    def stepBy(self, steps: int) -> None:
        """Step, then keep going if that landed on zero.

        The extra step carries the direction of travel, so stepping down
        from 1 reaches -1 and stepping up from -1 reaches 1.
        """
        super().stepBy(steps)
        if self.value() == 0:
            super().stepBy(1 if steps > 0 else -1)

    def setValue(self, value: int) -> None:
        super().setValue(self.replacement if value == 0 else value)

    def validate(self, text: str, position: int) -> object:
        state, checked, at = super().validate(text, position)
        if state == QValidator.State.Acceptable and self.isZeroText(checked):
            # Intermediate, not Invalid: it has to survive as a keystroke on
            # the way to 05, and fixup catches it if it is left standing.
            return QValidator.State.Intermediate, checked, at
        return state, checked, at

    def fixup(self, text: str) -> str:
        return str(self.replacement) if self.isZeroText(text) else text
