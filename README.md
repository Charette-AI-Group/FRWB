# File Rename Processing Workbench (FRWB)

Batch-rename the files of a folder from a pattern, with a live preview of every new name
before anything touches the disk. Built with PySide6.

## What it does

- **Choose a folder** and see its files on the left, the names they would get on the right.
  The two lists scroll and select together; each file has a check box to leave it out.
- **Double-click any row**, in either list, to open the file in its default application, the
  same as File Explorer. The right list shows names that do not exist yet, so a double-click
  there opens the file that row stands for.
- **Pattern** for the new name, with tokens: `{name}`, `{n}` counter, `{date}`, `{created}`,
  `{modified}`, `{taken}` (EXIF photo date), `{parent}` folder name, `{ext}`. A button per token
  inserts it at the cursor and wears a tick while it is in use; a *Presets* menu fills in common
  patterns. Anything outside braces is kept as typed, so `Holiday_{n}` works.
- **Number in name**: a number already in the name (`IMG_0042`) can be kept, replaced with a
  new counter, replaced with a date, or removed.
- **Counter**: start, step and zero-padded digits. It runs in the order of the list, which
  can be sorted by name (natural order, so `file2` comes before `file10`), created date,
  modified date or photo date. The three controls grey out until something uses the counter,
  which is either `{n}` in the pattern or *Replace With Counter*.
- **Date**: from the file's created or modified date, the photo's EXIF date, or a custom
  date/time you pick; any `strftime` format. These grey out in stages, since *Format* serves
  every date token while *Source* is read only for `{date}` and *Replace With Date*.
- **Find / Replace With**, **Name Case** and **Extension** case.
- **Conflicts and invalid names are shown**, never renamed: two files landing on one name, a
  name already in the folder, an empty name, a reserved Windows name.
- **Rename Files** turns teal once the batch can actually run, and applies it off the interface
  thread in two phases, so swaps and renumbering cannot overwrite anything. **File > Undo Last
  Rename** puts the last batch back.
- The folder, filter, sort and every rename setting are remembered between sessions.

**Website:** <https://charette-ai-group.github.io/FRWB/> — screenshots, the full manual and the
downloads, built from [`docs/`](docs/).

See [`docs/manual/README.md`](docs/manual/README.md) for the user manual (also under
**Help > User Manual**, F1).

## Icons

Generated, never hand-drawn — see [`src/frwb/resources/README.md`](src/frwb/resources/README.md):

```powershell
python tools\makeIcons.py
```

This writes the application icon (a multi-size `.ico` plus a 1024 px PNG for macOS) and a
glyph for each menu command, each drawn twice so it reads on both the light and the dark
theme. Every size is drawn at that size rather than shrunk from the largest. Previews and a
contact sheet of every icon at every size go to `.screenshots/`.

## One-time setup

```powershell
cd W:\projects\26FRWB
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Daily workflow

```powershell
cd W:\projects\26FRWB
.\.venv\Scripts\Activate.ps1
frwb
```

Or without the script entry point:

```powershell
python -m frwb.main
```

Or just double-click **`runApp.cmd`** in the project folder (needs the one-time setup done first).

## Tests and lint

```powershell
pytest
ruff check src tests tools
```

## Standalone builds

Users do not need Python. [Releases](https://github.com/Charette-AI-Group/FRWB/releases) carry a
Windows installer, a Windows portable zip and a macOS app bundle, all built by
[`.github/workflows/build.yml`](.github/workflows/build.yml) and attached automatically when a
version tag is pushed.

To build them yourself:

```powershell
pip install -e ".[build]"
python tools\buildExe.py
python tools\buildInstaller.py
```

| Step | Produces | Notes |
|------|----------|-------|
| `tools/buildExe.py` on Windows | `dist\FRWB\` | One-folder PyInstaller bundle, about 118 MB |
| `tools/buildExe.py` on macOS | `dist/FRWB.app` | Application bundle, from the same spec |
| `tools\buildInstaller.py` | `dist\frwbSetup-<version>.exe` | Inno Setup 6, about 34 MB. Per-user install, no administrator rights. Needs `winget install JRSoftware.InnoSetup`. Windows only |

The Windows build is one folder rather than one file so it starts immediately, and because an
installer wants a folder anyway. Either way `--selftest report.txt` asks a built copy whether it
kept its icons and its manual, which is the only way a windowed build can answer: it has no
console. The build script refuses to call a bundle shippable until it does.

### A note for macOS users

The app bundle is **not code-signed or notarised**, so Gatekeeper will refuse it on first open
with a message about an unidentified developer. Right-click the app and choose **Open**, which
offers a button the plain double-click does not, or clear the quarantine flag:

```bash
xattr -dr com.apple.quarantine FRWB.app
```

Signing needs a paid Apple Developer account, which this project does not have.

To publish a release, tag a commit whose `appConfig.appVersion` matches. The workflow refuses a
tag that disagrees, because a release named after a version the app does not report leaves a bug
report unanswerable.

```powershell
git tag -a v0.9.0 -m "First public beta" ; git push origin v0.9.0
```

## Structure

| Layer | Folder | Purpose |
|-------|--------|---------|
| Entry | `src/frwb/main.py` | Start `QApplication`, show main window |
| Config | `src/frwb/appConfig.py` | Paths, defaults, tokens, presets, date formats |
| UI | `src/frwb/ui/` | Widgets and dialogs only |
| Services | `src/frwb/services/` | Business logic (no Qt widgets) |
| Models | `src/frwb/models/` | Plain Python data types |

The rename feature, by file:

| File | Role |
|------|------|
| `models/renameModels.py` | `FileEntry`, `RenameSettings`, `RenamePreview`, the enums |
| `services/fileScanService.py` | List a folder, filter (`*.jpg; *.png`), natural sort |
| `services/exifService.py` | EXIF `DateTimeOriginal` from JPEG/TIFF, standard library only |
| `services/fileOpenService.py` | Hand a file to the shell, as a double-click in Explorer does |
| `services/renamePlanService.py` | Settings → new names, notes, conflict detection |
| `services/renameExecuteService.py` | Two-phase rename on disk, undo log |
| `services/workbenchStateService.py` | Remember folder and settings in `settings.ini` |
| `services/fileScanWorker.py`, `renameWorker.py` | The two `QThread`s |
| `services/taskbarService.py` | Claim the Windows taskbar identity, so the icon is ours |
| `ui/widgets/renameControlsPanel.py` | The controls above the panels |
| `ui/widgets/nonZeroSpinBox.py` | A spin box that steps over zero, for the counter step |
| `ui/widgets/fileListsPanel.py` | The two synchronised lists, summary, Rename button |
| `ui/appIcons.py` | Load the icons, in the ink the current theme needs |
| `ui/mainWindow.py` | Menus, wiring, workers |
| `tools/makeIcons.py` | Draw the icon set (not imported by the app) |

See `AGENTS.md` for architecture and naming conventions (for you and AI agents).

## License

MIT, see [`LICENSE`](LICENSE). © 2026 Charette AI Group, LLC.

---
*Created from the Qt App Template.*
