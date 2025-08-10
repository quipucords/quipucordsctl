"""Global configuration settings for quipucordsctl."""

import importlib.resources as pkg_resources
import logging
import pathlib

PROGRAM_NAME = "quipucordsctl"  # this program's executable command
SERVER_SOFTWARE_PACKAGE = "quipucords"  # used for constructing server's file paths
SERVER_SOFTWARE_NAME = "Quipucords"  # server's user-facing "product" name

COMMANDS_PACKAGE_PATH = str(pathlib.Path(__file__).parent.resolve() / "commands")

DEFAULT_LOG_LEVEL = logging.WARNING

_home = pathlib.Path.home()
SERVER_ENV_DIR = _home / f".config/{SERVER_SOFTWARE_PACKAGE}/env"
SERVER_DATA_DIR = _home / f".local/share/{SERVER_SOFTWARE_PACKAGE}"
SYSTEMD_UNITS_DIR = _home / ".config/containers/systemd"

_templates = pathlib.Path(str(pkg_resources.files("quipucordsctl"))) / "templates"
SYSTEMD_UNITS_TEMPLATES_DIR = _templates / "config"
ENV_TEMPLATES_DIR = _templates / "env"
