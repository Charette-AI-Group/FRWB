"""Reading the date a photo was taken, from EXIF, with the standard library.

Only the few bytes needed are read: the APP1 segment sits at the start of a
JPEG and cannot be longer than 64 KB, so one small read answers the question
for any file, however large the picture behind it.
"""

from __future__ import annotations

import datetime
import logging
import struct
from pathlib import Path

logger = logging.getLogger(__name__)

exifExtensions = frozenset({".jpg", ".jpeg", ".jpe", ".tif", ".tiff"})
# A JPEG segment length is a 16-bit field, so APP1 fits comfortably in this.
headerBytes = 70_000

tagDateTime = 0x0132
tagExifIfdPointer = 0x8769
tagDateTimeOriginal = 0x9003
tagDateTimeDigitized = 0x9004
exifDateFormat = "%Y:%m:%d %H:%M:%S"

IfdEntry = tuple[int, int, bytes]  # type, count, the raw four value bytes


def readTakenAt(path: Path) -> datetime.datetime | None:
    """The EXIF date, or None when the file has none or is not a photo."""
    if path.suffix.lower() not in exifExtensions:
        return None
    try:
        with open(path, "rb") as handle:
            data = handle.read(headerBytes)
        return takenAtFromBytes(data)
    except (OSError, ValueError, struct.error) as exc:
        logger.info("No EXIF date for %s: %s", path, exc)
        return None


def takenAtFromBytes(data: bytes) -> datetime.datetime | None:
    tiff = tiffBlock(data)
    if tiff is None:
        return None
    text = dateTextFromTiff(tiff)
    return parseExifDate(text) if text else None


def tiffBlock(data: bytes) -> bytes | None:
    """The TIFF structure holding the tags: the whole file, or JPEG's APP1."""
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return data
    if data[:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            return None
        marker = data[offset + 1]
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            offset += 2  # standalone markers carry no length
            continue
        if marker == 0xDA:
            return None  # image data begins; the headers are behind us
        (length,) = struct.unpack(">H", data[offset + 2 : offset + 4])
        if marker == 0xE1 and data[offset + 4 : offset + 10] == b"Exif\x00\x00":
            return data[offset + 10 : offset + 2 + length]
        offset += 2 + length
    return None


def dateTextFromTiff(tiff: bytes) -> str | None:
    """DateTimeOriginal first, then DateTimeDigitized, then plain DateTime."""
    order = {b"II": "<", b"MM": ">"}.get(tiff[:2])
    if order is None:
        return None
    (ifd0Offset,) = struct.unpack(order + "I", tiff[4:8])
    ifd0 = readIfd(tiff, order, ifd0Offset)
    exifIfd: dict[int, IfdEntry] = {}
    if tagExifIfdPointer in ifd0:
        (exifOffset,) = struct.unpack(order + "I", ifd0[tagExifIfdPointer][2])
        exifIfd = readIfd(tiff, order, exifOffset)
    for tag, ifd in (
        (tagDateTimeOriginal, exifIfd),
        (tagDateTimeDigitized, exifIfd),
        (tagDateTime, ifd0),
    ):
        if tag in ifd:
            text = asciiOf(tiff, order, ifd[tag])
            if text:
                return text
    return None


def readIfd(tiff: bytes, order: str, offset: int) -> dict[int, IfdEntry]:
    if offset + 2 > len(tiff):
        return {}
    (count,) = struct.unpack(order + "H", tiff[offset : offset + 2])
    entries: dict[int, IfdEntry] = {}
    for index in range(count):
        start = offset + 2 + index * 12
        chunk = tiff[start : start + 12]
        if len(chunk) < 12:
            break
        tag, valueType, valueCount = struct.unpack(order + "HHI", chunk[:8])
        entries[tag] = (valueType, valueCount, chunk[8:12])
    return entries


def asciiOf(tiff: bytes, order: str, entry: IfdEntry) -> str:
    _, count, raw = entry
    if count <= 4:
        payload = raw[:count]
    else:
        (valueOffset,) = struct.unpack(order + "I", raw)
        payload = tiff[valueOffset : valueOffset + count]
    return payload.split(b"\x00", 1)[0].decode("ascii", "ignore").strip()


def parseExifDate(text: str) -> datetime.datetime | None:
    """Cameras write '0000:00:00 00:00:00' for unknown; that is None too."""
    try:
        return datetime.datetime.strptime(text, exifDateFormat)
    except ValueError:
        return None
