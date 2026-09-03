r"""Build the standalone application, and check that what shipped is right.

PyInstaller succeeds cheerfully while leaving out a data file, and the symptom
turns up later as a window with no icon or a manual that will not open. So the
build is followed by an inventory of what actually landed in the bundle, and
then by the application's own --selftest, which is the only thing that proves
a windowed build starts at all: it has no console to print to.

    .venv\Scripts\python.exe tools\buildExe.py
    .venv\Scripts\python.exe tools\buildExe.py --no-selftest
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
specFile = projectRoot / "frwb.spec"
distDir = projectRoot / "dist" / "FRWB"
executable = distDir / "FRWB.exe"
reportFile = projectRoot / "dist" / "selftest.txt"
buildTimeoutSeconds = 1800.0
selfTestTimeoutSeconds = 180.0

# Everything the application reaches for at runtime, relative to the bundle's
# _internal folder, which is what sys._MEIPASS points at in a one-folder build
# and therefore what appConfig.bundleRoot becomes.
expectedPayload = [
    Path("frwb/resources/frwb.ico"),
    Path("frwb/resources/check-onDark.ico"),
    Path("frwb/resources/check-onLight.ico"),
    Path("frwb/resources/chooseFolder-onDark.ico"),
    Path("frwb/resources/chooseFolder-onLight.ico"),
    Path("frwb/resources/refresh-onDark.ico"),
    Path("frwb/resources/refresh-onLight.ico"),
    Path("frwb/resources/rename-onDark.ico"),
    Path("frwb/resources/rename-onLight.ico"),
    Path("frwb/resources/undo-onDark.ico"),
    Path("frwb/resources/undo-onLight.ico"),
    Path("docs/manual/README.md"),
]
# Nothing here belongs to a user, but a stray settings file or undo log would
# hand every install somebody else's folder and last batch.
refusedPayload = [
    Path("settings.ini"),
    Path("lastRename.json"),
]


def folderSize(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())


def humanSize(byteCount: int) -> str:
    return f"{byteCount / 1_000_000:.0f} MB"


def build() -> int:
    if distDir.exists():
        shutil.rmtree(distDir)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(specFile),
        "--noconfirm",
        "--clean",
        "--distpath",
        str(projectRoot / "dist"),
        "--workpath",
        str(projectRoot / "build"),
    ]
    print(f"$ {subprocess.list2cmdline(command)}")
    return subprocess.run(command, cwd=projectRoot, timeout=buildTimeoutSeconds).returncode


def internalDir() -> Path:
    """Where a one-folder build puts its data. _MEIPASS, at runtime."""
    candidate = distDir / "_internal"
    return candidate if candidate.is_dir() else distDir


def checkPayload() -> list[str]:
    problems: list[str] = []
    internal = internalDir()
    for relative in expectedPayload:
        if not (internal / relative).exists():
            problems.append(f"missing from the bundle: {relative}")
    for relative in refusedPayload:
        if (internal / relative).exists():
            problems.append(f"should not have shipped: {relative}")
    return problems


def runSelfTest() -> list[str]:
    """Start the built executable and ask it whether it is intact."""
    print(f"$ {executable} --selftest {reportFile}")
    try:
        completed = subprocess.run(
            [str(executable), "--selftest", str(reportFile)],
            cwd=distDir,
            timeout=selfTestTimeoutSeconds,
        )
    except subprocess.TimeoutExpired:
        return [f"--selftest did not finish within {selfTestTimeoutSeconds:.0f} s"]

    if reportFile.exists():
        print("\nWhat it reported:")
        for line in reportFile.read_text(encoding="utf-8").splitlines():
            print(f"  {line}")
    if completed.returncode != 0:
        return [f"--selftest failed with code {completed.returncode}"]
    if not reportFile.exists():
        return [f"--selftest wrote no report to {reportFile}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--no-selftest",
        action="store_true",
        help="skip launching the built executable (payload inventory only)",
    )
    arguments = parser.parse_args()

    code = build()
    if code != 0:
        print(f"\nPyInstaller failed with code {code}.")
        return code
    if not executable.exists():
        print(f"\nBuild reported success but {executable} is not there.")
        return 1

    problems = checkPayload()
    if not problems and not arguments.no_selftest:
        problems += runSelfTest()

    print()
    print(f"Bundle    : {distDir}")
    print(f"Executable: {executable.name} ({humanSize(executable.stat().st_size)})")
    print(f"Total     : {humanSize(folderSize(distDir))}")
    if problems:
        print("\nNOT SHIPPABLE:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nPayload is complete and the built application reports itself intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
