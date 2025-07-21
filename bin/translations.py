#!/usr/bin/env python3
"""
Extract translations for gettext to cover code *and* specific stdlib modules.

Simply invoking pybabel, xgettext, and similar tools on this project does not
automatically extract any strings gettext-wrapped inside Python's standard library
that we might expose to the end user (e.g. argparse). This script attempts to find
specific Python stdlib source files and include their strings with this project's
strings when exporting the messages.pot file.
"""

import pathlib
import subprocess
import sys
import sysconfig


def get_code_paths(source_code_dir: pathlib.Path, *stdlib_file_names: str) -> list:
    """Get a list of paths that contain gettext-wrapped strings to localize."""
    code_paths = [source_code_dir]
    stdlib_path = pathlib.Path(sysconfig.get_paths()["stdlib"])
    for stdlib_file_name in stdlib_file_names:
        stdlib_file_path = stdlib_path / stdlib_file_name
        if stdlib_file_path.exists():
            code_paths.append(stdlib_file_path)
    return code_paths


pybabel_path = pathlib.Path(sys.prefix) / "bin" / "pybabel"
source_code_dir = pathlib.Path(__file__).parent.parent / "quipucordsctl"
locales_dir = source_code_dir / "locale"
paths: list[str] = get_code_paths(source_code_dir, "argparse.py")
subprocess.run(  # noqa: S603
    [
        pybabel_path,
        "extract",
        "-o",
        str(locales_dir / "messages.pot"),
        *(str(path) for path in paths),
    ],
    check=False,
)
