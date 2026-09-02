# File Rename Processing Workbench

File Rename Processing Workbench (FRWB) - batch rename files with patterns, counters and dates (PySide6)

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
ruff check src tests
```

## Structure

| Layer | Folder | Purpose |
|-------|--------|---------|
| Entry | `src/frwb/main.py` | Start `QApplication`, show main window |
| Config | `src/frwb/appConfig.py` | Paths, defaults, app metadata |
| UI | `src/frwb/ui/` | Widgets and dialogs only |
| Services | `src/frwb/services/` | Business logic (no Qt widgets) |
| Models | `src/frwb/models/` | Plain Python data types |

See `AGENTS.md` for architecture and naming conventions (for you and AI agents).

---
*Created from the Qt App Template.*
