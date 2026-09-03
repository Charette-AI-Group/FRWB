"""Tests for the EXIF date reader, on JPEGs built here byte by byte."""

from __future__ import annotations

import datetime
import struct

from frwb.services import exifService as service


def tiffWithDates(
    order: str = "<", original: str | None = None, plain: str | None = None
) -> bytes:
    """A TIFF block: IFD0 (DateTime, ExifIFD pointer), then the Exif IFD."""
    entries0: list[tuple[int, bytes]] = []
    entriesExif: list[tuple[int, bytes]] = []
    values = bytearray()
    prefix = b"II*\x00" if order == "<" else b"MM\x00*"

    ifd0Offset = 8
    ifd0Size = 2 + 12 * (1 + (1 if plain else 0)) + 4
    exifOffset = ifd0Offset + ifd0Size
    exifSize = 2 + 12 * (1 if original else 0) + 4
    valuesOffset = exifOffset + exifSize

    def ascii(tag: int, text: str, into: list[tuple[int, bytes]]) -> None:
        payload = text.encode("ascii") + b"\x00"
        entry = struct.pack(order + "HHII", tag, 2, len(payload), valuesOffset + len(values))
        values.extend(payload)
        into.append((tag, entry))

    if plain:
        ascii(service.tagDateTime, plain, entries0)
    pointer = struct.pack(order + "HHII", service.tagExifIfdPointer, 4, 1, exifOffset)
    entries0.append((service.tagExifIfdPointer, pointer))
    if original:
        ascii(service.tagDateTimeOriginal, original, entriesExif)

    def ifd(entries: list[tuple[int, bytes]]) -> bytes:
        body = b"".join(entry for _, entry in entries)
        return struct.pack(order + "H", len(entries)) + body + b"\x00" * 4

    header = prefix + struct.pack(order + "I", ifd0Offset)
    return header + ifd(entries0) + ifd(entriesExif) + bytes(values)


def jpegWith(tiff: bytes) -> bytes:
    app1 = b"Exif\x00\x00" + tiff
    segment = b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
    return b"\xff\xd8" + segment + b"\xff\xda" + b"rest"


def testDateTimeOriginalIsRead() -> None:
    data = jpegWith(tiffWithDates(original="2021:07:04 12:30:45", plain="2022:01:01 00:00:00"))

    assert service.takenAtFromBytes(data) == datetime.datetime(2021, 7, 4, 12, 30, 45)


def testBigEndianIsReadToo() -> None:
    data = jpegWith(tiffWithDates(order=">", original="2021:07:04 12:30:45"))

    assert service.takenAtFromBytes(data) == datetime.datetime(2021, 7, 4, 12, 30, 45)


def testPlainDateTimeIsTheFallback() -> None:
    data = jpegWith(tiffWithDates(plain="2022:01:01 00:00:00"))

    assert service.takenAtFromBytes(data) == datetime.datetime(2022, 1, 1)


def testAJpegWithoutExifHasNoDate() -> None:
    assert service.takenAtFromBytes(b"\xff\xd8\xff\xdb\x00\x04\x00\x00\xff\xda") is None


def testNotAJpegAtAll() -> None:
    assert service.takenAtFromBytes(b"hello") is None
    assert service.takenAtFromBytes(b"") is None


def testTheUnknownDateCamerasWriteIsNone() -> None:
    assert service.parseExifDate("0000:00:00 00:00:00") is None


def testReadingFromDiskHonoursTheExtension(tmp_path) -> None:
    data = jpegWith(tiffWithDates(original="2021:07:04 12:30:45"))
    (tmp_path / "photo.JPG").write_bytes(data)
    (tmp_path / "photo.txt").write_bytes(data)

    assert service.readTakenAt(tmp_path / "photo.JPG") == datetime.datetime(2021, 7, 4, 12, 30, 45)
    assert service.readTakenAt(tmp_path / "photo.txt") is None
    assert service.readTakenAt(tmp_path / "missing.jpg") is None
