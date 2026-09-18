"""Get quipucordsctl's version from pyproject.toml."""

import sys
import tomllib
from pathlib import Path

major_minor = False

try:
    major_minor = sys.argv[1] == "--major-minor"
except IndexError:
    pass

toml_path = Path(__file__).absolute().parent.parent / "pyproject.toml"
with toml_path.open("rb") as fp:
    data = tomllib.load(fp)

output_version = data["project"]["version"]

if major_minor:
    output_version, _, _ = output_version.rpartition(".")

print(output_version)
