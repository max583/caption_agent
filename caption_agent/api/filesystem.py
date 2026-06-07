"""Server-side directory browser used by the create-batch folder picker (D-090).

The caption agent is a local single-user app bound to 127.0.0.1; the batch
``source_folder_path`` is a server-side path that the pipeline reads images from.
Exposing a directory listing to the same machine's browser is therefore the
intended way to let the user pick a folder without typing the absolute path.

The endpoint returns immediate subdirectories of ``path`` plus a count of image
files directly inside, so the picker can show which folders contain candidates.
"""

from __future__ import annotations

import os
import string
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/fs", tags=["filesystem"])

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _list_drives() -> list[str]:
    """Return available drive roots on Windows (e.g. ``['C:\\', 'D:\\']``).

    Empty on POSIX — there the natural starting point is ``/``.
    """
    if os.name != "nt":
        return []
    drives: list[str] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives


_PS_LNK_SCRIPT = (
    "$s = New-Object -ComObject WScript.Shell; "
    "while (($line = [Console]::ReadLine()) -ne $null) { $s.CreateShortcut($line).TargetPath }"
)


def _resolve_lnk_targets(lnk_paths: list[Path]) -> dict[str, str]:
    """Resolve Windows .lnk shortcuts to their target paths via PowerShell.

    Passes paths over stdin one-per-line so no shell-quoting is needed.
    Returns {str(lnk_path): target_path_str}; entries with empty targets are omitted.
    """
    if not lnk_paths or os.name != "nt":
        return {}
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_LNK_SCRIPT],
            input="\n".join(str(p) for p in lnk_paths),
            capture_output=True,
            text=True,
            timeout=5,
        )
        targets = result.stdout.splitlines()
        return {
            str(lnk): target.strip()
            for lnk, target in zip(lnk_paths, targets)
            if target.strip()
        }
    except Exception:  # noqa: BLE001
        return {}


def _empty(path: str, drives: list[str], error: str | None) -> dict[str, Any]:
    return {
        "path": path,
        "parent": None,
        "dirs": [],
        "image_count": 0,
        "drives": drives,
        "error": error,
    }


@router.get("/list")
def list_dir(path: str | None = Query(default=None)) -> dict[str, Any]:
    """List immediate subdirectories of ``path`` and count image files inside."""
    drives = _list_drives()

    # No path → starting point. On Windows show drives; on POSIX start at /.
    if not path:
        if drives:
            return {
                "path": "",
                "parent": None,
                "dirs": [{"name": d, "path": d} for d in drives],
                "image_count": 0,
                "drives": drives,
                "error": None,
            }
        path = "/"

    try:
        p = Path(path).expanduser()
        if not p.exists() or not p.is_dir():
            return _empty(str(p), drives, "Папка не найдена или это не директория")
        p = p.resolve()

        dirs: list[dict[str, str]] = []
        image_count = 0
        lnk_files: list[Path] = []
        for entry in sorted(p.iterdir(), key=lambda e: e.name.lower()):
            try:
                if entry.is_dir():
                    dirs.append({"name": entry.name, "path": str(entry)})
                elif entry.suffix.lower() == ".lnk":
                    lnk_files.append(entry)
                elif entry.suffix.lower() in _IMAGE_EXTENSIONS:
                    image_count += 1
            except OSError:
                # Skip individual entries we can't stat (broken symlinks etc.).
                continue

        # Resolve Windows .lnk shortcuts that point to directories.
        if lnk_files:
            for lnk_path, target in _resolve_lnk_targets(lnk_files).items():
                try:
                    target_p = Path(target)
                    if target_p.is_dir():
                        name = Path(lnk_path).stem  # filename without .lnk
                        dirs.append({"name": name + " →", "path": str(target_p)})
                except OSError:
                    continue
            dirs.sort(key=lambda d: d["name"].lower())

        # Drive root on Windows has parent == itself; treat that as "no parent"
        # so the UI can fall back to the drives list.
        parent = str(p.parent) if p.parent != p else None
        return {
            "path": str(p),
            "parent": parent,
            "dirs": dirs,
            "image_count": image_count,
            "drives": drives,
            "error": None,
        }
    except PermissionError:
        return _empty(path, drives, "Нет доступа к этой папке")
    except OSError as exc:
        return _empty(path, drives, str(exc)[:200])
