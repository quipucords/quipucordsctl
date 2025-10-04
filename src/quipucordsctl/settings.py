"""Global configuration settings for quipucordsctl."""

import logging
import pathlib

PROGRAM_NAME = "quipucordsctl"  # this program's executable command
SERVER_SOFTWARE_PACKAGE = "quipucords"  # used for constructing server's file paths
SERVER_SOFTWARE_NAME = "Quipucords"  # server's user-facing "product" name
ENV_VAR_PREFIX = "QUIPUCORDS_"  # used to construct env vars to bypass input prompts

COMMANDS_PACKAGE_PATH = str(pathlib.Path(__file__).parent.resolve() / "commands")

DEFAULT_LOG_LEVEL = logging.WARNING

_home = pathlib.Path.home()
SERVER_ENV_DIR = _home / f".config/{SERVER_SOFTWARE_PACKAGE}/env"
SERVER_DATA_DIR = _home / f".local/share/{SERVER_SOFTWARE_PACKAGE}"
SYSTEMD_UNITS_DIR = _home / ".config/containers/systemd"
SERVER_DATA_SUBDIRS = {
    data_dir: SERVER_DATA_DIR / data_dir
    for data_dir in ("certs", "data", "db", "log", "sshkeys")
}

# "Explicit is better than implicit." - PEP 20
# Do not glob the template directories. Use these definitions.
TEMPLATE_SYSTEMD_UNITS_RESOURCE_PATH = "templates/config"
TEMPLATE_SYSTEMD_UNITS_FILENAMES = (
    "quipucords.network",
    "quipucords-app.container",
    "quipucords-celery-worker.container",
    "quipucords-db.container",
    "quipucords-redis.container",
    "quipucords-server.container",
)
TEMPLATE_SERVER_ENV_RESOURCE_PATH = "templates/env"
TEMPLATE_SERVER_ENV_FILENAMES = (
    "env-ansible.env",
    "env-app.env",
    "env-celery-worker.env",
    "env-db.env",
    "env-redis.env",
    "env-server.env",
)


class RuntimeSettings:
    """A class to hold and manage global runtime settings."""

    def __init__(self):
        self._quiet: bool = False
        self._yes: bool = False

    def update(self, *, quiet: bool | None = None, yes: bool | None = None):
        """Update the global runtime settings."""
        if isinstance(quiet, bool):
            self._quiet = quiet
        if isinstance(yes, bool):
            self._yes = yes

    @property
    def quiet(self) -> bool:
        """Get the 'quiet' mode."""
        return self._quiet

    @property
    def yes(self) -> bool:
        """Get the 'yes' mode."""
        return self._yes


runtime = RuntimeSettings()
