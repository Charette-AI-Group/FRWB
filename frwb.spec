# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller build of the application. Driven by tools\buildExe.py.

A one-folder build rather than one-file, on purpose:

  - It starts immediately. A one-file build unpacks the whole Qt runtime to a
    temporary folder on every launch, which for a bundle this size is a wait
    before anything appears, every single time.
  - The installer wants a folder anyway, and an uninstaller that removes a
    folder is easier to reason about than one chasing a self-extractor.

What ships is the read-only half: the package and its icons, and the manual
that Help falls back to when there is no network. Everything the app writes
lives under APPDATA and is created on first run - see appConfig's settings
file and undo log.
"""

from pathlib import Path

projectRoot = Path(SPECPATH)

# PyInstaller does not collect package data on its own, and appConfig looks
# for the icons inside the package. Without this the executable wears the
# icon while the running window does not, which is a confusing half of the
# job: the taskbar looks right and the window looks unfinished.
datas = [
    (str(projectRoot / "src" / "frwb" / "resources"), "frwb/resources"),
    (str(projectRoot / "docs" / "manual"), "docs/manual"),
]

# Development-only, or simply never reached, and large enough to be worth
# refusing. Nothing here draws a chart, plays a video or renders a web page,
# and the Qt hook is otherwise happy to bring all three along.
excludes = [
    "pytest",
    "_pytest",
    "pytest_qt",
    "ruff",
    "tkinter",
    "PyInstaller",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtCharts",
    "PySide6.Qt3DCore",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtNetwork",
    "PySide6.QtSql",
    "PySide6.QtTest",
]

analysis = Analysis(
    [str(projectRoot / "src" / "frwb" / "main.py")],
    pathex=[str(projectRoot / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="FRWB",
    icon=str(projectRoot / "src" / "frwb" / "resources" / "frwb.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # No console: this is a windowed app, and a console behind a GUI is a
    # thing users close by accident, taking the app with it. --selftest
    # writes to a file for the same reason.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collected = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FRWB",
)
