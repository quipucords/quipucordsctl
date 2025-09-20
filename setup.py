#!/usr/bin/env python
"""A setuptools-based script for installing quipucordsctl."""

# Note: this is only used for RHEL 8 RPM builds as the
#       pyproject-rpm-macros is not made available by default.
#
#       With this, we can use the older py3_build/py3_install
#       but leverage the pyproject.toml content.

import setuptools

if __name__ == "__main__":
    setuptools.setup()

