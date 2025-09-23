#!/usr/bin/env python
"""A setuptools-based script for installing quipucordsctl."""

# Note: this is used for RHEL 8 and RHEL 9 RPM builds.
#       Note that on RHEL 8, the pyproject-rpm-macros is
#       not made available by default.
#
#       With this file, we can use the older py3_build/py3_install
#       but leverage the pyproject.toml content.

import setuptools

if __name__ == "__main__":
    setuptools.setup()
