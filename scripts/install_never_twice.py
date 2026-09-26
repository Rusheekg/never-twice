#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_never_twice.py — Install (or uninstall) the Never Twice Bob mode
into the global custom modes file so it is available in every project.

Global file locations
---------------------
  Bob IDE (all platforms): ~/.bob/settings/custom_modes.yaml
    Windows  : %USERPROFILE%\\.bob\\settings\\custom_modes.yaml
    macOS    : ~/.bob/settings/custom_modes.yaml
    Linux    : ~/.bob/settings/custom_modes.yaml

  Bob Shell (all platforms): ~/.bob/custom_modes.yaml
    (This script targets the IDE location by default.)

Slug conflict behaviour
-----------------------
  Project-level modes override global modes when both share the same slug.
  A project that already has its own .bob/custom_modes.yaml with a
  never-twice entry will continue to use that project definition; the global
  entry installed here acts as the fallback for projects that do NOT have one.

Usage
-----
  python install_never_twice.py              # install / update
  python install_never_twice.py --dry-run    # preview only, no writes
  python install_never_twice.py --uninstall  # remove the never-twice mode

Python 3.9+ compatible. Requires: PyYAML >= 6.0  (pip install -r requirements.txt)
"""

import argparse
import json
import pathlib
import shutil
import sys
import textwrap
from datetime import datetime
from typing import Optional

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required. Run:  pip install -r scripts/requirements.txt")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLUG = "never-twice"

# Path to the source-of-truth mode definition inside this repository.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_FILE = _REPO_ROOT / ".bob" / "custom_modes.yaml"

# Global file path (IDE).
# On all platforms Bob uses the user home directory; %USERPROFILE% on Windows
# is equivalent to ~ and pathlib.Path.home() resolves both correctly.
GLOBAL_FILE = pathlib.Path.home() / ".bob" / "settings" / "custom_modes.yaml"
# Legacy JSON path (supported for read; if found we migrate to YAML on write)
GLOBAL_FILE_JSON = pathlib.Path.home() / ".bob" / "settings" / "custom_modes.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_source_mode() -> dict:
    """Read the never-twice mode from the repository's .bob/custom_modes.yaml."""
    if not SOURCE_FILE.exists():
        sys.exit(f"ERROR: Source file not found: {SOURCE_FILE}")
    with SOURCE_FILE.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    modes = data.get("customModes", []) if isinstance(data, dict) else []
    for mode in modes:
        if isinstance(mode, dict) and mode.get("slug") == SLUG:
            return mode
    sys.exit(
        f"ERROR: Mode with slug '{SLUG}' not found in {SOURCE_FILE}. "
        "Has the source file been modified?"
    )


def _detect_global_file() -> tuple[pathlib.Path, str]:
    """
    Return (path, format) for the global modes file that should be used.

    Preference order:
      1. Existing YAML file   → use it (yaml)
      2. Existing JSON file   → use it, but output will be YAML (we migrate)
      3. Neither exists       → will create YAML at GLOBAL_FILE
    """
    if GLOBAL_FILE.exists():
        return GLOBAL_FILE, "yaml"
    if GLOBAL_FILE_JSON.exists():
        return GLOBAL_FILE_JSON, "json"
    return GLOBAL_FILE, "yaml"


def _read_global(path: pathlib.Path, fmt: str) -> dict:
    """Return parsed content of the global modes file as a dict."""
    with path.open("r", encoding="utf-8") as fh:
        raw = fh.read()
    if fmt == "json":
        data = json.loads(raw)
    else:
        data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        data = {}
    if "customModes" not in data:
        data["customModes"] = []
    return data


def _write_global(path: pathlib.Path, data: dict, dry_run: bool) -> None:
    """Serialise *data* to YAML and write (or print in dry-run mode)."""
    output = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    if dry_run:
        print("\n--- DRY-RUN: content that WOULD be written ---")
        print(output)
        print("--- end ---\n")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")


def _make_backup(path: pathlib.Path, dry_run: bool) -> Optional[pathlib.Path]:
    """Create a timestamped backup of *path* and return the backup path."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = path.with_name(path.name + f".bak-{ts}")
    if dry_run:
        print(f"DRY-RUN: would create backup → {backup}")
        return backup
    shutil.copy2(path, backup)
    return backup


def _verify(path: pathlib.Path) -> tuple[bool, str]:
    """
    Read the file back and verify:
      - it parses correctly
      - exactly one never-twice entry exists
      - return (ok, message)
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001
        return False, f"FAIL — parse error: {exc}"
    modes = data.get("customModes", []) if isinstance(data, dict) else []
    nt_entries = [m for m in modes if isinstance(m, dict) and m.get("slug") == SLUG]
    count = len(nt_entries)
    if count == 1:
        return True, f"PASS — file parses correctly; exactly 1 '{SLUG}' entry present."
    return False, f"FAIL — expected 1 '{SLUG}' entry, found {count}."


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install(dry_run: bool = False) -> None:
    mode_to_install = _load_source_mode()
    global_path, fmt = _detect_global_file()
    backup_path: pathlib.Path | None = None

    print(f"\nGlobal modes file : {global_path}")
    print(f"Source repository : {SOURCE_FILE}")

    if global_path.exists():
        data = _read_global(global_path, fmt)
        modes: list = data.setdefault("customModes", [])
        other_modes_before = [m for m in modes if not (isinstance(m, dict) and m.get("slug") == SLUG)]
        existing_idx = next(
            (i for i, m in enumerate(modes) if isinstance(m, dict) and m.get("slug") == SLUG),
            None,
        )

        backup_path = _make_backup(global_path, dry_run)
        if not dry_run:
            print(f"Backup created    : {backup_path}")
        print(
            "NOTE: Comments and custom formatting in the global file may be "
            "normalised by PyYAML when the file is rewritten. "
            "The backup keeps your original."
        )

        if existing_idx is not None:
            action = "Replacing existing"
            modes[existing_idx] = mode_to_install
        else:
            action = "Adding new"
            modes.append(mode_to_install)

        data["customModes"] = other_modes_before + [
            m for m in modes if isinstance(m, dict) and m.get("slug") == SLUG
        ]
        # Ensure ordering: all other modes first, then never-twice at end
        other_modes = [m for m in modes if not (isinstance(m, dict) and m.get("slug") == SLUG)]
        nt_mode = [m for m in modes if isinstance(m, dict) and m.get("slug") == SLUG]
        data["customModes"] = other_modes + nt_mode

        print(f"\nAction: {action} '{SLUG}' entry.")
        print(f"Other modes in file: {len(other_modes)} (unchanged)")

        # If source was JSON and we are now writing to YAML path, update path
        target_path = GLOBAL_FILE if fmt == "json" else global_path
        _write_global(target_path, data, dry_run)
        if fmt == "json" and not dry_run:
            print(f"(Migrated from legacy JSON to YAML at {target_path})")
    else:
        # File does not exist — create it from scratch
        print("Global file does not exist — will create it.")
        data = {"customModes": [mode_to_install]}
        print(f"\nAction: Creating new file with '{SLUG}' entry.")
        _write_global(global_path, data, dry_run)

    if not dry_run:
        ok, msg = _verify(global_path if global_path.exists() else GLOBAL_FILE)
        print(f"\nVerification: {msg}")
    else:
        print("\n(Verification skipped in dry-run mode — no file was written.)")


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

def uninstall(dry_run: bool = False) -> None:
    global_path, fmt = _detect_global_file()

    print(f"\nGlobal modes file : {global_path}")

    if not global_path.exists():
        print(f"Nothing to uninstall — '{global_path}' does not exist.")
        return

    data = _read_global(global_path, fmt)
    modes: list = data.get("customModes", [])
    before = len(modes)
    remaining = [m for m in modes if not (isinstance(m, dict) and m.get("slug") == SLUG)]
    removed = before - len(remaining)

    if removed == 0:
        print(f"Mode '{SLUG}' not found in the global file — nothing to remove.")
        return

    backup_path = _make_backup(global_path, dry_run)
    if not dry_run:
        print(f"Backup created    : {backup_path}")
    print(
        "NOTE: Comments and custom formatting in the global file may be "
        "normalised by PyYAML when the file is rewritten. "
        "The backup keeps your original."
    )

    data["customModes"] = remaining
    print(f"\nAction: Removing '{SLUG}' entry ({removed} entry removed).")
    print(f"Other modes in file: {len(remaining)} (unchanged)")

    _write_global(global_path, data, dry_run)

    if not dry_run:
        ok, msg = _verify(global_path)
        # After uninstall the mode should be ABSENT — adjust verification message
        modes_after = yaml.safe_load(global_path.read_text(encoding="utf-8")) or {}
        nt_after = [
            m for m in modes_after.get("customModes", [])
            if isinstance(m, dict) and m.get("slug") == SLUG
        ]
        if len(nt_after) == 0:
            print(f"\nVerification: PASS — '{SLUG}' entry successfully removed; file parses correctly.")
        else:
            print(f"\nVerification: FAIL — '{SLUG}' entry still present after uninstall.")
    else:
        print("\n(Verification skipped in dry-run mode — no file was written.)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""\
            Install the Never Twice Bob mode into your global custom modes file
            so it is available in every project without copying files.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the never-twice mode from the global file (creates a backup first).",
    )
    args = parser.parse_args()

    if args.dry_run and args.uninstall:
        print("Dry-run uninstall preview:")
        uninstall(dry_run=True)
    elif args.uninstall:
        uninstall(dry_run=False)
    elif args.dry_run:
        install(dry_run=True)
    else:
        install(dry_run=False)


if __name__ == "__main__":
    main()
