# Bundled resources

Files the application loads at runtime. Paths come from
[`appConfig.py`](../appConfig.py) — never build one by hand, because a bundled
build reads them from the extraction directory rather than from the source
tree, and `appConfig` is what knows the difference.

Everything in this folder ships in the wheel.

## Icons

All generated, following the approach the sibling application pySPWB uses for
its own. **Do not edit the files** — edit the drawing and run it again:

```powershell
python tools\makeIcons.py            # all of them, or name the ones you want
python tools\makeIcons.py undo       # just this one
```

| File | Used for | Found through |
|---|---|---|
| `frwb.ico` | The application, Windows and Linux | `appConfig.iconFile()` |
| `frwb.png` | The application, macOS — 1024×1024 | `appConfig.iconFile()` |
| `chooseFolder-onLight.ico` / `-onDark.ico` | File > Choose Folder, and the button | `appConfig.actionIconFile("chooseFolder", onDark)` |
| `refresh-onLight.ico` / `-onDark.ico` | File > Refresh | `... ("refresh", onDark)` |
| `rename-onLight.ico` / `-onDark.ico` | File > Rename Files, and the button | `... ("rename", onDark)` |
| `undo-onLight.ico` / `-onDark.ico` | File > Undo Last Rename | `... ("undo", onDark)` |
| `check-onLight.ico` / `-onDark.ico` | The tick on a token button in use | `... ("check", onDark)` |

The application `.ico` carries **16, 24, 32, 48, 64, 128 and 256 px**; the
command glyphs carry **16 through 64**, since a menu never shows one large.
Every size is *drawn* at that size rather than shrunk from the largest: below
about 24 px a scaled-down rendering loses its strokes and turns to mush, so
the generator thickens lines and drops detail as it goes down. The application
icon drops the sheet behind it below 32 px and its written lines below 48.

## Two inks, because there are two themes

Help > Theme switches this app between light and dark, so each glyph is drawn
twice: `-onLight` in near-black for a light theme, `-onDark` in near-white for
a dark one. `ui/appIcons.py` picks by asking Qt what colour the
window is actually being painted, which also answers the third case — the
default, where the theme follows Windows and the app is never told which way
it went.

The choice is remade in `changeEvent` on `PaletteChange`, not in the theme
menu handler: Qt delivers the new palette *after* the theme is applied, so a
glyph chosen while handling the click is chosen from the colours being
replaced.

## The artwork

The application is a sheet of paper being written on — the file whose name is
changing — on a teal tile. The tile colour is the point: pySPWB is gold and
CloakClip is indigo, so on a taskbar holding all three the one to click is
found before it is read.

If a file is missing the application runs without that icon rather than
failing: `iconFile()` and `actionIconFile()` both return `None`, and
`ui/appIcons.py` hands back an empty `QIcon`. `tests/testUi/testAppIcons.py`
checks that each file exists, carries every size it claims, differs from the
others and from its own other ink, and is actually worn by the command it
belongs to.

Previews for review, including a contact sheet of every icon at every size,
are written to `.screenshots/` by the generator.
