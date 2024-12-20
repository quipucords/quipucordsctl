"""Global configuration settings for quipucordsctl."""

import logging
import pathlib

PROGRAM_NAME = "quipucordsctl"
SERVER_SOFTWARE = "quipucords"
SERVER_SOFTWARE_NAME = "Quipucords"

COMMANDS_PACKAGE_PATH = str(pathlib.Path(__file__).parent.resolve() / "commands")

DEFAULT_LOG_LEVEL = logging.WARNING

_home = pathlib.Path.home()
SERVER_ENV_DIR = _home / f".config/{SERVER_SOFTWARE}/env"
SERVER_DATA_DIR = _home / f".local/share/{SERVER_SOFTWARE}"
SYSTEMD_UNITS_DIR = _home / ".config/containers/systemd"

# TODO maybe use pkg_resources.resource_filename when packaging
_templates = pathlib.Path(__file__).parent.parent.resolve() / "templates"
SYSTEMD_UNITS_TEMPLATES_DIR = _templates / "config"
ENV_TEMPLATES_DIR = _templates / "env"
