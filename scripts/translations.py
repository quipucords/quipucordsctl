#!/usr/bin/env python3
"""
Process translations for gettext strings in our code *and* specific stdlib modules.

Simply invoking pybabel, xgettext, and similar tools on this project does not
automatically extract any strings gettext-wrapped inside Python's standard library
that we might expose to the end user (e.g. argparse). This script attempts to find
specific Python stdlib source files and include their strings with this project's
strings when exporting the messages.pot file.

LOCALES should include a list of two-letter language codes (e.g. "pt")
that we intend to localize/translate. See here for lists of valid codes:
https://www.gnu.org/software/gettext/manual/html_node/Usual-Language-Codes.html
https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
"""

import argparse
import pathlib
import re
import subprocess
import sys
import sysconfig

DOMAIN = "messages"
PYBABEL_BIN = pathlib.Path(sys.prefix) / "bin" / "pybabel"
SOURCE_PATH = pathlib.Path("src/quipucordsctl")
SOURCE_CODE_DIR = pathlib.Path(__file__).parent.parent / SOURCE_PATH
LOCALES_DIR = SOURCE_CODE_DIR / "locale"
PYTHON_STDLIB_FILES = ["argparse.py"]
LOCALES = ["en"]


def get_code_paths() -> list:
    """Get a list of paths that contain gettext-wrapped strings to localize."""
    code_paths = [SOURCE_PATH]
    stdlib_path = pathlib.Path(sysconfig.get_paths()["stdlib"])
    for stdlib_file_name in PYTHON_STDLIB_FILES:
        stdlib_file_path = stdlib_path / stdlib_file_name
        if stdlib_file_path.exists():
            code_paths.append(stdlib_file_path)
    return code_paths


def normalize_stdlib_location_comments(pot_file: pathlib.Path) -> None:
    """Normalize stdlib location comments to remove environment-specific paths.

    pybabel writes the full path to stdlib files (e.g. argparse.py) in location
    comments, which varies across Python installations and environments. Replace the
    path prefix with '...' so the comment is stable across contributors.

    Before: #: ../../../../.pyenv/versions/3.12.5/lib/python3.12/argparse.py:228
    After:  #: .../python3.12/argparse.py:228
    """
    stdlib_file_pattern = re.compile(
        r"(#: ).*/(python\d+\.\d+/" + "|".join(PYTHON_STDLIB_FILES) + r":\d+)"
    )
    text = pot_file.read_text(encoding="utf-8")
    normalized = stdlib_file_pattern.sub(r"\1.../\2", text)
    pot_file.write_text(normalized, encoding="utf-8")


def translations_extract(pybabel_bin):
    """Extract gettext-wrapped strings to messages.pot template file."""
    paths: list[str] = get_code_paths()
    pot_file = LOCALES_DIR / f"{DOMAIN}.pot"
    try:
        subprocess.check_call(  # noqa: S603
            [
                pybabel_bin,
                "extract",
                "-o",
                str(pot_file),
                *(str(path) for path in paths),
            ],
        )
    except subprocess.CalledProcessError as e:
        print(f"Error invoking pybabel extract: {e}")
        sys.exit(1)
    normalize_stdlib_location_comments(pot_file)


def translations_update(pybabel_bin):
    """Update locale-specific .po files from the .pot template file."""
    for locale in LOCALES:
        locale_path = LOCALES_DIR / locale / "LC_MESSAGES" / f"{DOMAIN}.po"
        subcommand = "update" if locale_path.exists() else "init"
        try:
            subprocess.check_call(  # noqa: S603
                [
                    pybabel_bin,
                    subcommand,
                    "-i",
                    str(LOCALES_DIR / f"{DOMAIN}.pot"),
                    "-d",
                    str(LOCALES_DIR),
                    "-D",
                    DOMAIN,
                    "-l",
                    locale,
                ],
            )
        except subprocess.CalledProcessError as e:
            print(f"Error invoking pybabel {subcommand} for locale {locale}: {e}")
            sys.exit(1)


def translations_compile(pybabel_bin):
    """Compile locale-specific .mo files from the .po files."""
    try:
        subprocess.check_call(  # noqa: S603
            [
                pybabel_bin,
                "compile",
                "-d",
                str(LOCALES_DIR),
                "-D",
                DOMAIN,
            ],
        )
    except subprocess.CalledProcessError as e:
        print(f"Error invoking pybabel compile: {e}")
        sys.exit(1)


def main():
    """Parse CLI args to invoke requested command."""
    parser = argparse.ArgumentParser(
        description="Translation management script using pybabel."
    )
    parser.add_argument(
        "--pybabel", type=str, required=False, help="pybabel command to use"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )
    subparsers.add_parser("extract", help="Extract strings to .pot file")
    subparsers.add_parser("update", help="Update translation .po files")
    subparsers.add_parser("compile", help="Compile binary .mo files")
    args = parser.parse_args()

    pybabel_bin = pathlib.Path(args.pybabel) if args.pybabel else PYBABEL_BIN
    if args.command == "extract":
        translations_extract(pybabel_bin)
    elif args.command == "update":
        translations_update(pybabel_bin)
    elif args.command == "compile":
        translations_compile(pybabel_bin)


if __name__ == "__main__":
    main()
