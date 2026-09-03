"""Draw the application icon and the action icons.

Every icon is drawn with QPainter *at each size* rather than scaled down from
one big rendering, because a 16 px icon made by shrinking a 256 px one is
mush - the strokes fall below a pixel and the shape stops reading. The
per-size drawing thickens strokes and drops detail as it gets smaller.

The application icon is a sheet of paper being written on, on a teal tile:
renaming a file, and a colour of its own so a taskbar holding several
Charette AI Group applications keeps them apart.

The action icons are single-colour glyphs for the commands the window
offers. Each is drawn twice, once in dark ink for a light theme and once in
light ink for a dark one, because this application ships a theme switch and
a fixed-colour glyph would disappear into one of the two.

    python tools/makeIcons.py [names ...]

Writes into ``src/frwb/resources/``, which ships in the wheel. The
application finds them through ``appConfig`` - never by path.
"""

from __future__ import annotations

import math
import os
import struct
import sys
from pathlib import Path

# Must happen before QApplication exists: the offscreen plugin has no fonts,
# and the contact sheet labels its rows. Painting into a QPixmap opens no
# window, so the native plugin costs nothing here.
os.environ.pop("QT_QPA_PLATFORM", None)

repoRoot = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repoRoot / "src"))

outputDir = repoRoot / "src" / "frwb" / "resources"
reviewDir = repoRoot / ".screenshots"

from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

#: What the application .ico carries. 16 is the taskbar and the title bar,
#: 256 the file dialog's extra-large view; the ones between are what Windows
#: actually picks at various DPI settings.
appIconSizes = (16, 24, 32, 48, 64, 128, 256)
#: Action icons live in menus and on buttons and are never shown large.
actionIconSizes = (16, 24, 32, 48, 64)

#: The application tile: teal, where the sibling applications are gold and
#: indigo, so the three are told apart on a taskbar before they are read.
tileTop = QColor("#2DD4BF")
tileBottom = QColor("#0F766E")
sheetColour = QColor("#FFFFFF")
#: the sheet behind the first one: this renames a folder full of files
sheetBehindColour = QColor(255, 255, 255, 115)
#: the writing on the sheet, and the pencil doing it
inkOnSheet = QColor("#0F766E")
pencilColour = QColor("#FBBF24")

#: Action glyphs: near-black on a light theme, near-white on a dark one.
inkOnLight = QColor("#1F2937")
inkOnDark = QColor("#E5E7EB")

application: QApplication | None = None


def session() -> QApplication:
    global application
    if application is None:
        application = QApplication.instance() or QApplication([])
    return application


# ---------------------------------------------------------------- helpers --


def strokeWidth(size: int, weight: float = 1.0) -> float:
    """A stroke that stays visible when the icon is tiny.

    Scaling a stroke linearly with the icon makes it vanish below about
    24 px, so the floor is one whole pixel and small sizes get a
    proportionally fatter line.
    """
    return max(1.0, size * 0.075 * weight)


def strokePen(colour: QColor, size: int, weight: float = 1.0) -> QPen:
    pen = QPen(colour, strokeWidth(size, weight))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def polyline(points: list[QPointF]) -> QPainterPath:
    path = QPainterPath()
    for index, point in enumerate(points):
        (path.moveTo if index == 0 else path.lineTo)(point)
    return path


def contentBox(size: int, inset: float) -> QRectF:
    """Where artwork may go, as a fraction of the icon inset on every side."""
    margin = size * inset
    return QRectF(margin, margin, size - 2 * margin, size - 2 * margin)


def pointOnArc(box: QRectF, degrees: float) -> QPointF:
    """Qt's arc angles: degrees counterclockwise from 3 o'clock."""
    radians = math.radians(degrees)
    return QPointF(
        box.center().x() + box.width() / 2 * math.cos(radians),
        box.center().y() - box.height() / 2 * math.sin(radians),
    )


def arrowHead(
    painter: QPainter, tip: QPointF, heading: QPointF, size: int, weight: float = 1.0
) -> None:
    """A filled triangle at ``tip``, pointing along ``heading``."""
    length = math.hypot(heading.x(), heading.y()) or 1.0
    forward = QPointF(heading.x() / length, heading.y() / length)
    side = QPointF(-forward.y(), forward.x())
    reach = strokeWidth(size, weight) * 1.9
    base = QPointF(tip.x() - forward.x() * reach, tip.y() - forward.y() * reach)

    head = QPainterPath()
    head.moveTo(tip)
    head.lineTo(base.x() + side.x() * reach * 0.72, base.y() + side.y() * reach * 0.72)
    head.lineTo(base.x() - side.x() * reach * 0.72, base.y() - side.y() * reach * 0.72)
    head.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(painter.brush().color())
    painter.fillPath(head, painter.brush())


def sheetPath(box: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(box, radius, radius)
    return path


# ----------------------------------------------------- the application icon --


def drawApplication(painter: QPainter, size: int) -> None:
    """A sheet being written on: the file whose name is changing.

    Below 32 px the sheet behind it and the writing are dropped - at that
    size they are sub-pixel smudges that only blur the two shapes that do
    carry the meaning, the sheet and the pencil.
    """
    box = contentBox(size, 0.19)
    small = size < 32
    radius = size * 0.06

    sheetWidth = box.width() * 0.64
    sheetBox = QRectF(box.left(), box.top(), sheetWidth, box.height() * 0.92)

    if not small:
        behind = QRectF(sheetBox)
        behind.translate(box.width() * 0.13, -box.height() * 0.06)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(sheetBehindColour)
        painter.drawPath(sheetPath(behind, radius))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(sheetColour)
    painter.drawPath(sheetPath(sheetBox, radius))

    if size >= 48:
        # two short lines: a name, and the room to write another
        painter.setPen(strokePen(inkOnSheet, size, 0.42))
        for fraction in (0.30, 0.50):
            y = sheetBox.top() + sheetBox.height() * fraction
            painter.drawLine(
                QPointF(sheetBox.left() + sheetBox.width() * 0.18, y),
                QPointF(sheetBox.right() - sheetBox.width() * 0.18, y),
            )

    # the pencil, crossing the lower right so it reads as writing on the sheet
    painter.setPen(strokePen(pencilColour, size, 1.5 if small else 1.25))
    painter.drawLine(
        QPointF(box.left() + box.width() * 0.42, box.bottom()),
        QPointF(box.right(), box.top() + box.height() * 0.42),
    )


# --------------------------------------------------------- the action icons --


def drawChooseFolder(painter: QPainter, size: int, ink: QColor) -> None:
    """A folder: the tab, then the body over it."""
    box = contentBox(size, 0.10)
    radius = size * 0.07
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ink)

    tab = QRectF(
        box.left(),
        box.top() + box.height() * 0.10,
        box.width() * 0.46,
        box.height() * 0.30,
    )
    painter.drawPath(sheetPath(tab, radius))
    body = QRectF(
        box.left(),
        box.top() + box.height() * 0.26,
        box.width(),
        box.height() * 0.64,
    )
    painter.drawPath(sheetPath(body, radius))


def drawRefresh(painter: QPainter, size: int, ink: QColor) -> None:
    """A circle that does not quite close, with a head on the open end."""
    weight = 1.15
    inset = strokeWidth(size, weight) / 2 + size * 0.12
    box = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)

    start, sweep = 70.0, 290.0
    arc = QPainterPath()
    arc.arcMoveTo(box, start)
    arc.arcTo(box, start, -sweep)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(strokePen(ink, size, weight))
    painter.drawPath(arc)

    # the head sits at the end of the sweep, pointing the way the arc travels
    endAngle = start - sweep
    tip = pointOnArc(box, endAngle)
    radians = math.radians(endAngle)
    painter.setBrush(ink)
    arrowHead(painter, tip, QPointF(-math.sin(radians), -math.cos(radians)), size, weight)


def drawRename(painter: QPainter, size: int, ink: QColor) -> None:
    """A sheet with a pencil across it: the application icon in one colour."""
    box = contentBox(size, 0.11)
    small = size < 24
    radius = size * 0.07
    sheetBox = QRectF(
        box.left(), box.top() + box.height() * 0.04, box.width() * 0.62, box.height() * 0.92
    )

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(strokePen(ink, size, 0.8))
    painter.drawPath(sheetPath(sheetBox, radius))

    if not small:
        painter.setPen(strokePen(ink, size, 0.55))
        for fraction in (0.33, 0.55):
            y = sheetBox.top() + sheetBox.height() * fraction
            painter.drawLine(
                QPointF(sheetBox.left() + sheetBox.width() * 0.22, y),
                QPointF(sheetBox.right() - sheetBox.width() * 0.22, y),
            )

    painter.setPen(strokePen(ink, size, 1.3))
    painter.drawLine(
        QPointF(box.left() + box.width() * 0.54, box.bottom()),
        QPointF(box.right(), box.top() + box.height() * 0.30),
    )


def drawUndo(painter: QPainter, size: int, ink: QColor) -> None:
    """A return arrow: up the right, round the corner, back to a head on the left.

    Not the circular arrow the obvious drawing would use - that is what
    Refresh already is, and two rings a menu apart are one ring as far as a
    reader is concerned.
    """
    weight = 1.15
    box = contentBox(size, 0.14)
    shaftY = box.top() + box.height() * 0.74
    riserX = box.right() - box.width() * 0.06
    corner = box.width() * 0.30
    headReach = strokeWidth(size, weight) * 1.9

    path = QPainterPath()
    path.moveTo(QPointF(riserX, box.top()))
    path.lineTo(QPointF(riserX, shaftY - corner))
    path.quadTo(QPointF(riserX, shaftY), QPointF(riserX - corner, shaftY))
    path.lineTo(QPointF(box.left() + headReach, shaftY))

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(strokePen(ink, size, weight))
    painter.drawPath(path)

    painter.setBrush(ink)
    arrowHead(painter, QPointF(box.left(), shaftY), QPointF(-1.0, 0.0), size, weight)


def drawCheck(painter: QPainter, size: int, ink: QColor) -> None:
    """A tick, for the token buttons: this one is in the pattern.

    Drawn small inside its square. It sits beside a label on a button rather
    than alone in a menu, so it has to read at a glance without shouting.
    """
    box = contentBox(size, 0.15)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(strokePen(ink, size, 1.3))
    painter.drawPath(
        polyline(
            [
                QPointF(box.left(), box.top() + box.height() * 0.52),
                QPointF(box.left() + box.width() * 0.36, box.bottom()),
                QPointF(box.right(), box.top()),
            ]
        )
    )


#: file stem -> what draws it. The application icon is drawn on its own tile,
#: the rest are glyphs drawn twice, once for each theme.
actionDesigns = {
    "chooseFolder": drawChooseFolder,
    "refresh": drawRefresh,
    "rename": drawRename,
    "undo": drawUndo,
    "check": drawCheck,
}
applicationKey = "frwb"


# ------------------------------------------------------ rendering and packing --


def renderApplication(size: int) -> QPixmap:
    session()
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # tighter corners when small, or the rounding eats the artwork
    radius = size * (0.18 if size < 32 else 0.22)
    tile = QLinearGradient(QPointF(0, 0), QPointF(0, size))
    tile.setColorAt(0.0, tileTop)
    tile.setColorAt(1.0, tileBottom)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(tile)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    drawApplication(painter, size)
    painter.end()
    return pixmap


def renderAction(key: str, size: int, onDark: bool) -> QPixmap:
    session()
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    actionDesigns[key](painter, size, inkOnDark if onDark else inkOnLight)
    painter.end()
    return pixmap


def pngBytes(pixmap: QPixmap) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


def packIco(images: list[tuple[int, bytes]]) -> bytes:
    """A multi-resolution .ico holding PNG-encoded entries.

    Written by hand rather than through Qt's writer so every size in the file
    is the one that was drawn at that size. Vista and later accept PNG inside
    an ICO, which is what keeps the 256 px entry from being enormous.
    """
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, payload = [], []
    for size, data in images:
        entries.append(
            struct.pack(
                "<BBBBHHII",
                0 if size >= 256 else size,  # 0 means 256 in an ICO
                0 if size >= 256 else size,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        payload.append(data)
        offset += len(data)
    return header + b"".join(entries) + b"".join(payload)


def report(path: Path, sizes: tuple[int, ...]) -> None:
    listed = "/".join(str(size) for size in sizes)
    print(f"   {path.name:24} {path.stat().st_size / 1024:6.1f} kB  ({listed})")


def buildApplication() -> None:
    images = [(size, pngBytes(renderApplication(size))) for size in appIconSizes]
    ico = outputDir / f"{applicationKey}.ico"
    ico.write_bytes(packIco(images))
    report(ico, appIconSizes)

    # macOS has no use for .ico, and wants the big one
    png = outputDir / f"{applicationKey}.png"
    renderApplication(1024).save(str(png), "PNG")
    print(f"   {png.name:24} {png.stat().st_size / 1024:6.1f} kB  (1024)")

    renderApplication(256).save(str(reviewDir / f"icon-{applicationKey}.png"), "PNG")


def buildAction(key: str) -> None:
    for onDark in (False, True):
        variant = "onDark" if onDark else "onLight"
        images = [
            (size, pngBytes(renderAction(key, size, onDark))) for size in actionIconSizes
        ]
        ico = outputDir / f"{key}-{variant}.ico"
        ico.write_bytes(packIco(images))
        report(ico, actionIconSizes)
        renderAction(key, 128, onDark).save(
            str(reviewDir / f"icon-{key}-{variant}.png"), "PNG"
        )


def writeContactSheet(path: Path) -> None:
    """Every icon at every size, each on the ground it is drawn for.

    The whole point of drawing per size is what happens at 16 px, and that
    cannot be judged from a folder of 256 px previews.
    """
    session()
    rows = (
        [(applicationKey, None)]
        + [(key, False) for key in actionDesigns]
        + [(key, True) for key in actionDesigns]
    )
    sizes = (16, 24, 32, 48, 64, 128)
    cell, labelWidth, headerHeight = 148, 190, 34

    sheet = QPixmap(labelWidth + cell * len(sizes), headerHeight + cell * len(rows))
    sheet.fill(QColor("#9CA3AF"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setFont(QFont("Segoe UI", 9))

    for column, size in enumerate(sizes):
        painter.setPen(QColor("#111827"))
        painter.drawText(
            QRectF(labelWidth + column * cell, 6, cell, headerHeight - 10),
            int(Qt.AlignmentFlag.AlignCenter),
            f"{size} px",
        )

    for row, (key, onDark) in enumerate(rows):
        top = headerHeight + row * cell
        ground = QColor("#1F2430") if onDark else QColor("#F3F4F6")
        painter.fillRect(QRectF(labelWidth, top, cell * len(sizes), cell - 6), ground)
        painter.setPen(QColor("#111827"))
        label = key if onDark is None else f"{key}  ({'onDark' if onDark else 'onLight'})"
        painter.drawText(
            QRectF(8, top, labelWidth - 16, cell - 6),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            label,
        )
        for column, size in enumerate(sizes):
            pixmap = (
                renderApplication(size)
                if onDark is None
                else renderAction(key, size, onDark)
            )
            painter.drawPixmap(
                int(labelWidth + column * cell + (cell - size) / 2),
                int(top + (cell - 6 - size) / 2),
                pixmap,
            )
    painter.end()
    sheet.save(str(path), "PNG")
    print(f"\n   {path.name:24} {path.stat().st_size / 1024:6.1f} kB  (contact sheet)")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    known = [applicationKey, *actionDesigns]
    wanted = arguments[1:] or known
    unknown = [name for name in wanted if name not in known]
    if unknown:
        raise SystemExit(f"unknown icon(s) {unknown}; known: {known}")

    outputDir.mkdir(parents=True, exist_ok=True)
    reviewDir.mkdir(parents=True, exist_ok=True)
    print(f"drawing {len(wanted)} icon(s) -> {outputDir}\n")
    for key in wanted:
        if key == applicationKey:
            buildApplication()
        else:
            buildAction(key)
    if wanted == known:
        writeContactSheet(reviewDir / "icon-contact-sheet.png")
    print(f"\nDone. Previews for review in {reviewDir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
