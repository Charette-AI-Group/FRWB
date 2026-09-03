"""Application configuration — paths, defaults, and metadata."""

from __future__ import annotations

import os
import sys
from pathlib import Path

appName = "File Rename Processing Workbench"
appShortName = "FRWB"
appVersion = "0.1.0"
organizationName = "Charette-AI-Group"

# Help > About contents
editorName = "Francois Charette, PhD"
aiAgentName = "Claude - Fable 5.1"
copyrightHolder = "Charette AI Group, LLC"
repoUrl = "https://github.com/Charette-AI-Group/frwb"

# Donate button, shared across the Charette AI Group applications so they look
# like they come from the same place.
donateUrl = "https://www.paypal.com/donate/?hosted_button_id=FEM4WLD7LHY36"
donateColour = "#f0b232"
donateTextColour = "#1f1e1b"
donatePressedColour = "#d9991f"

projectRoot = Path(__file__).resolve().parents[2]

# In a bundled build the package lives inside an archive rather than on disk,
# so bundled files come from the extraction directory instead. Getting this
# wrong is the classic "works from source, no icon in the .exe" bug.
if getattr(sys, "frozen", False):
    resourcesDir = Path(getattr(sys, "_MEIPASS", projectRoot)) / "resources"
else:
    resourcesDir = Path(__file__).resolve().parent / "resources"

# Icons, drawn by tools/makeIcons.py into resourcesDir. Every path is asked
# for through the two functions below, never built by hand, so a build that
# moves the files only has to change this file.
applicationIconStem = "frwb"
#: One glyph per command the window offers, plus the tick the token buttons
#: wear. Each is drawn twice: this app ships a light/dark switch, and a
#: fixed-colour glyph vanishes into one of them.
actionIconKeys = ("chooseFolder", "refresh", "rename", "undo", "check")


def iconFile() -> Path | None:
    """The application icon, or None when it has not been generated.

    macOS has no use for a .ico and wants the large PNG; everything else
    takes the multi-size .ico.
    """
    name = f"{applicationIconStem}.png" if sys.platform == "darwin" else (
        f"{applicationIconStem}.ico"
    )
    path = resourcesDir / name
    return path if path.is_file() else None


def actionIconFile(key: str, onDark: bool) -> Path | None:
    """One command's glyph for the background it will sit on, or None."""
    if key not in actionIconKeys:
        raise ValueError(f"unknown action icon {key!r}; expected one of {actionIconKeys}")
    path = resourcesDir / f"{key}-{'onDark' if onDark else 'onLight'}.ico"
    return path if path.is_file() else None

# Help > User Manual. The copy in the checkout is what a new app has, and it is
# enough: the menu item works from the first run rather than being a promise.
manualPath = projectRoot / "docs" / "manual" / "README.md"
# Publishing is opt-in. Set this once the manual is pushed somewhere that
# renders markdown and the published copy becomes the preferred one, with the
# local copy as the offline fallback. Left empty no network request is made.
#     manualUrl = f"{repoUrl}/blob/main/docs/manual/README.md"
manualUrl = ""
# How long to wait for the published copy before falling back to the local one.
manualTimeoutSeconds = 3.0

appDataDir = Path(os.environ.get("APPDATA", str(Path.home()))) / appName
settingsFile = appDataDir / "settings.ini"
# The last batch of renames, so File > Undo Last Rename can put it back.
undoLogFile = appDataDir / "lastRename.json"
windowTitle = f"{appShortName} - {appName}"
defaultWindowWidth = 1200
defaultWindowHeight = 760

# Rename defaults and the choices offered in the controls panel.
defaultPattern = "{name}"
defaultFileFilter = "*"
defaultDateFormat = "%Y%m%d_%H%M%S"
dateFormatChoices = (
    "%Y%m%d_%H%M%S",
    "%Y-%m-%d_%H-%M-%S",
    "%Y%m%d",
    "%Y-%m-%d",
    "%Y%m%d-%H%M",
    "%Y-%m",
    "%Y",
)
# Tokens the pattern understands, in the order the Insert Token menu lists them.
patternTokens = (
    ("name", "Original name, after the number and find/replace steps"),
    ("n", "Counter"),
    ("date", "Date from the selected source, in the selected format"),
    ("created", "File created date"),
    ("modified", "File modified date"),
    ("taken", "Photo taken date, from EXIF"),
    ("parent", "Name of the folder"),
    ("ext", "Original extension, without the dot"),
)
patternPresets = (
    ("Keep Name", "{name}"),
    ("Name + Counter", "{name}_{n}"),
    ("Counter + Name", "{n}_{name}"),
    ("Date + Counter", "{date}_{n}"),
    ("Date + Name", "{date}_{name}"),
    ("Folder Name + Counter", "{parent}_{n}"),
)
# Preview colours, chosen to read on both the light and the dark palette.
conflictColour = "#e0503c"
invalidColour = "#d98c1f"

# The Rename button once the batch can actually run. Both are the teal of the
# application icon, taken from opposite ends of its tile, because a button
# that paints its own ground has to be read against that ground rather than
# against the theme: deep teal under white on a light theme, the icon's bright
# teal under near-black on a dark one. Every pair clears 4.5:1 against its own
# text, which testFileListsPanel checks rather than trusts.
renameReadyOnLight = {
    "background": "#0F766E",
    "text": "#FFFFFF",
    "hover": "#0C6058",
    "pressed": "#0A544E",
}
renameReadyOnDark = {
    "background": "#2DD4BF",
    "text": "#0B1220",
    "hover": "#5EE7D6",
    "pressed": "#14B8A6",
}
# How long the preview waits after the last keystroke before recomputing.
previewDelayMilliseconds = 150
