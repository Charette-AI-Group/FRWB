# File Rename Processing Workbench — user manual

FRWB renames all the files of a folder at once. You describe the new name with a pattern,
watch the result on the right before anything happens, then press **Rename Files**. If the
result is not what you wanted, **File > Undo Last Rename** puts every file back.

## 1. Choose the folder

Press **Choose Folder...** (or `Ctrl+O`). The files appear in the left list, the names they
would get in the right list. Nothing is renamed yet.

- **Filter** narrows the list: `*.jpg; *.png` keeps only those. Press Enter to apply.
- **Sort By** sets the order of the list, which is also the order the counter counts in.
  *Name* uses natural order (`file2` before `file10`); *Photo Taken* uses the EXIF date.
- **Check boxes**: untick a file to leave it out. **All** / **None** tick or untick every file.
- Hover a file on the left for its created, modified and photo dates.
- **Double-click a file to open it** in whatever application Windows uses for that kind of
  file, exactly as File Explorer does. This works in both lists. The right list shows names
  that do not exist yet, so double-clicking there opens the file that row stands for, under
  its current name. Nothing is renamed by opening a file.

Press `F5` (**File > Refresh**) if the folder changed behind the app's back.

## 2. Describe the new name

Two boxes do this:

- **Name Pattern** — the template the new name is built from.
- **Name Modifiers** — changes to the text itself, made either side of that template.

Both work on the name without its extension. The extension is kept unless you change its case
in *Name Modifiers*.

### Name Pattern

The pattern is the new name, with tokens in braces replaced for each file:

| Token | Becomes |
|-------|---------|
| `{name}` | The original name, after the *Number In Name* and *Find* steps below |
| `{n}` | The counter |
| `{date}` | The date from the *Date* box, in its format |
| `{created}` / `{modified}` | The file's created or modified date, same format |
| `{taken}` | The photo's EXIF date (falls back to the modified date if there is none) |
| `{parent}` | The folder's name |
| `{ext}` | The original extension without its dot |

Under the field is a **button for each token**. Clicking one adds it at the cursor, and each
button shows a **tick while its token is in the pattern**, so the row tells you at a glance what
the new name is made of.

The buttons insert; they do not switch. Click `{n}` twice and you get it twice. That is
deliberate, because a pattern is ordered and can hold text of your own, and neither survives
being reduced to eight switches:

- `{name}_{n}` and `{n}_{name}` are different results from the same two tokens.
- `Holiday_{n}` puts a word you chose in front of every file. Anything outside braces is kept
  exactly as typed.

**Presets** offers ready-made patterns such as `{name}_{n}` or `{date}_{n}`. Picking one fills
the field, and the ticks follow by themselves. A token that is misspelled is left as typed, so
you see it in the preview rather than losing it.

### Find / Replace With

Plain text replaced inside the original name, before the pattern is applied. Leave *Replace
With* empty to delete the text.

### Name Case / Extension

Keep, lower, UPPER or Title case for the name; keep, lower or UPPER for the extension.

## 3. The number already in the name

Cameras and downloads number files: `IMG_0042.jpg`, `Scan 12.pdf`. The **Number In Name**
box says what happens to that number:

| Existing Number | Result for `IMG_0042` |
|-----------------|-----------------------|
| Keep | `IMG_0042` |
| Replace With Counter | `IMG_001`, `IMG_002`, ... in list order |
| Replace With Date | `IMG_20240102_030405` from the *Date* box |
| Remove | `IMG` (the separator goes with it) |

**Which One** chooses the last or the first number when a name holds several
(`2024_pic_07`).

## 4. Counter and date

- **Counter**: *Start*, *Step* and *Digits* (3 gives `001`). It runs in list order and skips
  unticked files. *Step* counts down when negative, and goes straight from 1 to -1: a step of
  zero would give every file the same number, so it is not offered.

  The three counter controls are **greyed out until something uses the counter**. Two things
  do: `{n}` somewhere in the pattern, or *Existing Number* set to *Replace With Counter*.
  Either one wakes them up.
- **Date**: *Source* is the file's created date, its modified date, the photo's EXIF date, or
  a **Custom** date/time you pick. *Format* uses Python `strftime` codes: `%Y` year,
  `%m` month, `%d` day, `%H` hour, `%M` minute, `%S` second. Type your own or pick one.

  These grey out **in stages**, because they are not one switch:

  | Control | Live when |
  |---|---|
  | *Format* | any date token is in the pattern — `{date}`, `{created}`, `{modified}`, `{taken}` — or *Existing Number* is *Replace With Date*. Every one of them is printed through the format |
  | *Source* | `{date}` is in the pattern, or *Existing Number* is *Replace With Date*. The other three tokens name their own date, so there is nothing for *Source* to pick |
  | *Custom* | *Source* is live **and** set to *Custom Date/Time* |

  So a pattern of `{created}` leaves *Format* live and *Source* greyed: you can change how the
  date is printed, but not which date it is.

## 5. Read the right list, then rename

| Colour | Meaning |
|--------|---------|
| Normal | Will be renamed |
| Gray | Unchanged, or unticked |
| Red | **Conflict**: two files would get the same name, or the name is already taken in the folder |
| Orange | **Invalid**: empty name, or a name Windows reserves such as `CON` |

Hover a name for the reason. The summary line under the lists counts each kind, and
**Rename Files** (`Ctrl+R`) stays disabled while any conflict or invalid name remains.

The button **turns teal the moment the batch can run**, so the go-ahead is visible without
reading the summary line. It goes back to plain grey whenever something blocks it, or while a
rename is already running.

Renaming is done in two steps so that swapping names or renumbering a series never
overwrites a file. Files that could not be renamed are listed in a dialog; the rest are done.

## 6. Undo

**File > Undo Last Rename** (`Ctrl+Shift+Z`) puts the files of the last batch back to their
previous names. Only the most recent batch is kept.

## Remembered between sessions

The folder, filter, sort order and every setting above come back the next time the app
opens. **Help > Theme** chooses light, dark, or the Windows setting.
