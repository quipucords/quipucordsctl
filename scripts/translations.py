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
import sys
import sysconfig

from babel.messages.frontend import (
    CommandLineInterface,
)

DOMAIN = "messages"
SOURCE_CODE_DIR = pathlib.Path(__file__).parent.parent / "src" / "quipucordsctl"
LOCALES_DIR = SOURCE_CODE_DIR / "locale"
PYTHON_STDLIB_FILES = ["argparse.py"]
LOCALES = ["en"]
BABEL_COMMAND = "pybabel"


def babel_call(args):
    """Invoke the command via the python3-babel provided command line interface."""
    try:
        CommandLineInterface().run(args)
    except (
        FileNotFoundError,
    ) as e:
        print(f"Error invoking {args} error: {e}")
        sys.exit(1)


def get_code_paths() -> list:
    """Get a list of paths that contain gettext-wrapped strings to localize."""
    code_paths = [SOURCE_CODE_DIR]
    stdlib_path = pathlib.Path(sysconfig.get_paths()["stdlib"])
    for stdlib_file_name in PYTHON_STDLIB_FILES:
        stdlib_file_path = stdlib_path / stdlib_file_name
        if stdlib_file_path.exists():
            code_paths.append(stdlib_file_path)
    return code_paths


def translations_extract():
    """Extract gettext-wrapped strings to messages.pot template file."""
    paths: list[str] = get_code_paths()
    babel_call(
        [
            BABEL_COMMAND,
            "extract",
            "-o",
            str(LOCALES_DIR / f"{DOMAIN}.pot"),
            *(str(path) for path in paths),
        ],
    )


def translations_update():
    """Update locale-specific .po files from the .pot template file."""
    for locale in LOCALES:
        locale_path = LOCALES_DIR / locale / "LC_MESSAGES" / f"{DOMAIN}.po"
        subcommand = "update" if locale_path.exists() else "init"
        babel_call(  # noqa: S603
            [
                BABEL_COMMAND,
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


def translations_compile():
    """Compile locale-specific .mo files from the .po files."""
    babel_call(  # noqa: S603
        [
            BABEL_COMMAND,
            "compile",
            "-d",
            str(LOCALES_DIR),
            "-D",
            DOMAIN,
        ],
    )


def main():
    """Parse CLI args to invoke requested command."""
    parser = argparse.ArgumentParser(
        description="Translation management script using pybabel."
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )
    subparsers.add_parser("extract", help="Extract strings to .pot file")
    subparsers.add_parser("update", help="Update translation .po files")
    subparsers.add_parser("compile", help="Compile binary .mo files")
    args = parser.parse_args()

    if args.command == "extract":
        translations_extract()
    elif args.command == "update":
        translations_update()
    elif args.command == "compile":
        translations_compile()


if __name__ == "__main__":
    main()
