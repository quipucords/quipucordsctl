"""Sphinx configuration for quipucordsctl man page generation."""

# Project information with placeholders for variable substitution
project = "QUIPUCORDSCTL_VAR_PROGRAM_NAME"
copyright = (
    "QUIPUCORDSCTL_VAR_CURRENT_YEAR, Red Hat, Inc. "
    "Licensed under the GNU General Public License version 3."
)
author = "Red Hat, Inc."
release = "PKG_VERSION"

# Use man-template as the root document directly (no index.rst needed)
root_doc = "man-template"

# Man page output configuration
# Format: (source, name, description, authors, section)
man_pages = [
    (
        "man-template",
        "QUIPUCORDSCTL_VAR_PROGRAM_NAME",
        "Deploy and manage QUIPUCORDSCTL_VAR_PROJECT in Podman containers",
        [author],
        1,  # section 1 = user commands
    ),
]

# Minimal extensions (none needed for basic man pages)
extensions = []

# Suppress warnings
suppress_warnings = ["man.unknown_section"]
