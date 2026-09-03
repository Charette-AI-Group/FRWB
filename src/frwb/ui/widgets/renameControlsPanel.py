"""The controls above the two panels: what the new names are made of.

Every control change is announced through settingsChanged; the window asks
for currentSettings() and rebuilds the preview. Nothing here touches files.
"""

from __future__ import annotations

from PySide6.QtCore import QDateTime, QEvent, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from frwb import appConfig
from frwb.models.renameModels import (
    CaseMode,
    DateSource,
    NumberMode,
    NumberPosition,
    RenameSettings,
)
from frwb.services import renamePlanService
from frwb.ui import appIcons
from frwb.ui.widgets.nonZeroSpinBox import NonZeroSpinBox

#: Why a group can be greyed out, said where the greying happens. Each is kept
#: to one line: wrapped, it is clipped by the height the row gives the group.
counterHint = "Used by {n} and Replace With Counter."
dateHint = "Used by the date tokens. Source applies to {date} only."

#: The tick beside a token button, and the blank that holds its place.
tokenIconSize = QSize(13, 13)

numberModeLabels = {
    NumberMode.keep: "Keep",
    NumberMode.counter: "Replace With Counter",
    NumberMode.date: "Replace With Date",
    NumberMode.remove: "Remove",
}
numberPositionLabels = {
    NumberPosition.last: "Last Number",
    NumberPosition.first: "First Number",
}
dateSourceLabels = {
    DateSource.created: "File Created",
    DateSource.modified: "File Modified",
    DateSource.taken: "Photo Taken (EXIF)",
    DateSource.custom: "Custom Date/Time",
}
nameCaseLabels = {
    CaseMode.keep: "Keep",
    CaseMode.lower: "lower case",
    CaseMode.upper: "UPPER CASE",
    CaseMode.title: "Title Case",
}
extensionCaseLabels = {
    CaseMode.keep: "Keep",
    CaseMode.lower: "lower case",
    CaseMode.upper: "UPPER CASE",
}


def comboFrom(labels: dict) -> QComboBox:
    combo = QComboBox()
    for value, label in labels.items():
        combo.addItem(label, value)
    return combo


def selectData(combo: QComboBox, value: object) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


class RenameControlsPanel(QWidget):
    settingsChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.isApplying = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.buildPatternGroup())
        layout.addWidget(self.buildModifierGroup())
        row = QHBoxLayout()
        row.addWidget(self.buildNumberGroup())
        row.addWidget(self.buildCounterGroup())
        row.addWidget(self.buildDateGroup(), 1)
        layout.addLayout(row)

        self.connectSignals()
        self.rebuildTokenIcons()
        self.refreshIndicators()

    # --- building ----------------------------------------------------------

    def buildPatternGroup(self) -> QGroupBox:
        """The template the new name is built from, and the ways to fill it in."""
        group = self.patternGroup = QGroupBox("Name Pattern")
        column = QVBoxLayout(group)

        self.patternEdit = QLineEdit(appConfig.defaultPattern)
        self.patternEdit.setObjectName("patternEdit")
        self.patternEdit.setPlaceholderText("e.g. {name}_{n}  or  Holiday_{n}")
        self.patternEdit.setToolTip(
            "The new name without its extension. Tokens in braces are replaced,\n"
            "and anything else is kept as typed."
        )
        self.presetsButton = self.menuButton("Presets", self.buildPresetMenu())

        top = QHBoxLayout()
        top.addWidget(QLabel("Pattern:"))
        top.addWidget(self.patternEdit, 1)
        top.addWidget(self.presetsButton)
        column.addLayout(top)
        column.addLayout(self.buildTokenRow())
        return group

    def buildTokenRow(self) -> QHBoxLayout:
        """A button per token, out in the open rather than behind a menu.

        Each carries a tick while its token is in the pattern, so the row
        reads as what the name is made of. The tick reports; it does not
        control. Clicking always inserts, because a pattern is ordered and
        holds text of its own, and neither survives being reduced to eight
        switches: {name}_{n} and {n}_{name} would be the same two switches.
        """
        row = QHBoxLayout()
        row.addWidget(QLabel("Tokens:"))
        self.tokenButtons: dict[str, QToolButton] = {}
        for token, description in appConfig.patternTokens:
            button = QToolButton()
            button.setText(f"{{{token}}}")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIconSize(tokenIconSize)
            button.setToolTip(f"{description}.\nClick to add it at the cursor.")
            button.clicked.connect(lambda checked=False, name=token: self.insertToken(name))
            row.addWidget(button)
            self.tokenButtons[token] = button
        row.addStretch(1)
        return row

    def buildModifierGroup(self) -> QGroupBox:
        """Changes made to the text itself, either side of the pattern.

        Find and Replace run on the original name before the pattern reads it;
        the two case controls run on what the pattern produced.
        """
        group = self.modifierGroup = QGroupBox("Name Modifiers")
        row = QHBoxLayout(group)

        self.findEdit = QLineEdit()
        self.findEdit.setObjectName("findEdit")
        self.findEdit.setPlaceholderText("text in the name")
        self.replaceEdit = QLineEdit()
        self.replaceEdit.setObjectName("replaceEdit")
        self.replaceEdit.setPlaceholderText("leave empty to delete it")
        self.nameCaseCombo = comboFrom(nameCaseLabels)
        self.extensionCaseCombo = comboFrom(extensionCaseLabels)

        row.addWidget(QLabel("Find:"))
        row.addWidget(self.findEdit, 2)
        row.addWidget(QLabel("Replace With:"))
        row.addWidget(self.replaceEdit, 2)
        row.addWidget(QLabel("Name Case:"))
        row.addWidget(self.nameCaseCombo)
        row.addWidget(QLabel("Extension:"))
        row.addWidget(self.extensionCaseCombo)
        return group

    def buildNumberGroup(self) -> QGroupBox:
        group = QGroupBox("Number In Name")
        form = QFormLayout(group)
        self.numberModeCombo = comboFrom(numberModeLabels)
        self.numberModeCombo.setToolTip(
            "What happens to a number already in the name, such as the 0042 in IMG_0042."
        )
        self.numberPositionCombo = comboFrom(numberPositionLabels)
        form.addRow("Existing Number:", self.numberModeCombo)
        form.addRow("Which One:", self.numberPositionCombo)
        return group

    def buildCounterGroup(self) -> QGroupBox:
        group = self.counterGroup = QGroupBox("Counter  {n}")
        form = QFormLayout(group)
        self.counterStartSpin = QSpinBox()
        self.counterStartSpin.setRange(0, 999_999_999)
        self.counterStartSpin.setValue(1)
        self.counterStepSpin = NonZeroSpinBox()
        self.counterStepSpin.setRange(-1000, 1000)
        self.counterStepSpin.setValue(1)
        self.counterStepSpin.setToolTip(
            "How much the counter moves per file. Negative counts down.\n"
            "Zero is skipped: it would give every file the same number."
        )
        self.counterDigitsSpin = QSpinBox()
        self.counterDigitsSpin.setRange(1, 12)
        self.counterDigitsSpin.setValue(3)
        self.counterDigitsSpin.setToolTip("Minimum digits, padded with zeros: 3 gives 001.")
        form.addRow("Start:", self.counterStartSpin)
        form.addRow("Step:", self.counterStepSpin)
        form.addRow("Digits:", self.counterDigitsSpin)

        # Always present, and dimmed like the legend under the lists: when the
        # group is greyed out this is the only thing left to say why, since a
        # disabled control takes no mouse events and so shows no tooltip.
        self.counterHintLabel = QLabel(counterHint)
        self.counterHintLabel.setEnabled(False)
        form.addRow(self.counterHintLabel)
        return group

    def buildDateGroup(self) -> QGroupBox:
        group = self.dateGroup = QGroupBox("Date  {date}")
        form = self.dateForm = QFormLayout(group)
        self.dateSourceCombo = comboFrom(dateSourceLabels)
        self.dateFormatCombo = QComboBox()
        self.dateFormatCombo.setEditable(True)
        self.dateFormatCombo.addItems(list(appConfig.dateFormatChoices))
        self.dateFormatCombo.setToolTip(
            "Python strftime codes: %Y year, %m month, %d day, %H hour, %M minute, %S second."
        )
        self.customDateEdit = QDateTimeEdit(QDateTime.currentDateTime())
        self.customDateEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.customDateEdit.setCalendarPopup(True)
        form.addRow("Source:", self.dateSourceCombo)
        form.addRow("Format:", self.dateFormatCombo)
        form.addRow("Custom:", self.customDateEdit)

        self.dateHintLabel = QLabel(dateHint)
        self.dateHintLabel.setEnabled(False)
        form.addRow(self.dateHintLabel)
        return group

    def menuButton(self, text: str, menu: QMenu) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        return button

    def buildPresetMenu(self) -> QMenu:
        menu = QMenu(self)
        for label, pattern in appConfig.patternPresets:
            action = menu.addAction(f"{label}   {pattern}")
            action.triggered.connect(lambda checked=False, p=pattern: self.patternEdit.setText(p))
        return menu

    def connectSignals(self) -> None:
        for edit in (self.patternEdit, self.findEdit, self.replaceEdit):
            edit.textChanged.connect(self.emitChanged)
        for combo in (
            self.numberModeCombo,
            self.numberPositionCombo,
            self.nameCaseCombo,
            self.extensionCaseCombo,
            self.dateSourceCombo,
        ):
            combo.currentIndexChanged.connect(self.emitChanged)
        for spin in (self.counterStartSpin, self.counterStepSpin, self.counterDigitsSpin):
            spin.valueChanged.connect(self.emitChanged)
        self.dateFormatCombo.currentTextChanged.connect(self.emitChanged)
        self.customDateEdit.dateTimeChanged.connect(self.emitChanged)

    # --- behaviour ---------------------------------------------------------

    def insertToken(self, token: str) -> None:
        self.patternEdit.insert(f"{{{token}}}")
        self.patternEdit.setFocus()

    def setRowEnabled(self, form: QFormLayout, field: QWidget, enabled: bool) -> None:
        """Grey one row of a form, its label with it.

        QFormLayout has no row-level enable, and greying the control while
        its label stays black reads as a control that is merely busy.
        """
        field.setEnabled(enabled)
        label = form.labelForField(field)
        if label is not None:
            label.setEnabled(enabled)

    def refreshCounterAvailability(self) -> None:
        """Grey the counter out while nothing in the name would use it."""
        self.counterGroup.setEnabled(renamePlanService.usesCounter(self.currentSettings()))

    def refreshDateAvailability(self) -> None:
        """Grey the date controls out one at a time: they are not one switch.

        Format serves every date token, Source serves only {date}, and Custom
        serves only a Source set to it. So {created} on its own leaves Format
        live and Source with nothing to pick.
        """
        settings = self.currentSettings()
        sourceIsUsed = renamePlanService.usesDate(settings)
        self.dateGroup.setEnabled(renamePlanService.usesDateFormat(settings))
        self.setRowEnabled(self.dateForm, self.dateSourceCombo, sourceIsUsed)
        self.setRowEnabled(
            self.dateForm,
            self.customDateEdit,
            sourceIsUsed and settings.dateSource == DateSource.custom,
        )

    def rebuildTokenIcons(self) -> None:
        """The tick, and a blank of exactly its size.

        The blank is what keeps the labels still as tokens come and go: an
        empty QIcon reserves no room, a transparent one reserves the same
        room the tick will need.
        """
        self.checkIcon = appIcons.actionIcon("check")
        blank = QPixmap(tokenIconSize)
        blank.fill(Qt.GlobalColor.transparent)
        self.blankIcon = QIcon(blank)

    def refreshTokenButtons(self) -> None:
        """Tick the tokens the pattern is actually using."""
        present = renamePlanService.patternTokenNames(self.patternEdit.text())
        for token, button in self.tokenButtons.items():
            button.setIcon(self.checkIcon if token in present else self.blankIcon)

    def refreshIndicators(self) -> None:
        """Everything that follows the settings rather than sets them."""
        self.refreshCounterAvailability()
        self.refreshDateAvailability()
        self.refreshTokenButtons()

    def changeEvent(self, event: QEvent) -> None:
        # The tick's ink comes from the palette, which Qt delivers after the
        # theme has been applied.
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self.rebuildTokenIcons()
            self.refreshTokenButtons()

    def emitChanged(self, *_args: object) -> None:
        if self.isApplying:
            return
        self.refreshIndicators()
        self.settingsChanged.emit()

    def currentSettings(self) -> RenameSettings:
        # Qt hands the stored enum back as its plain string value, so each one
        # is turned back into the member the services compare against.
        return RenameSettings(
            pattern=self.patternEdit.text(),
            numberMode=NumberMode(self.numberModeCombo.currentData()),
            numberPosition=NumberPosition(self.numberPositionCombo.currentData()),
            counterStart=self.counterStartSpin.value(),
            counterStep=self.counterStepSpin.value(),
            counterDigits=self.counterDigitsSpin.value(),
            dateSource=DateSource(self.dateSourceCombo.currentData()),
            dateFormat=self.dateFormatCombo.currentText(),
            customDate=self.customDateEdit.dateTime().toPython(),
            findText=self.findEdit.text(),
            replaceText=self.replaceEdit.text(),
            nameCase=CaseMode(self.nameCaseCombo.currentData()),
            extensionCase=CaseMode(self.extensionCaseCombo.currentData()),
        )

    def applySettings(self, settings: RenameSettings) -> None:
        """Set every control at once, announcing a single change at the end."""
        self.isApplying = True
        try:
            self.patternEdit.setText(settings.pattern)
            selectData(self.numberModeCombo, settings.numberMode)
            selectData(self.numberPositionCombo, settings.numberPosition)
            self.counterStartSpin.setValue(settings.counterStart)
            self.counterStepSpin.setValue(settings.counterStep)
            self.counterDigitsSpin.setValue(settings.counterDigits)
            selectData(self.dateSourceCombo, settings.dateSource)
            self.dateFormatCombo.setCurrentText(settings.dateFormat)
            if settings.customDate is not None:
                self.customDateEdit.setDateTime(
                    QDateTime.fromSecsSinceEpoch(int(settings.customDate.timestamp()))
                )
            self.findEdit.setText(settings.findText)
            self.replaceEdit.setText(settings.replaceText)
            selectData(self.nameCaseCombo, settings.nameCase)
            selectData(self.extensionCaseCombo, settings.extensionCase)
        finally:
            self.isApplying = False
        self.refreshIndicators()
        self.settingsChanged.emit()
