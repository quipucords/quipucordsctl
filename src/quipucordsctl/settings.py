"""Global configuration settings for quipucordsctl."""

import logging
import os
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
SERVER_DATA_SUBDIRS_EXCLUDING_DB = {
    data_dir: SERVER_DATA_DIR / data_dir
    for data_dir in ("certs", "data", "log", "sshkeys")
}
SERVER_DATA_SUBDIRS = dict(
    sorted((SERVER_DATA_SUBDIRS_EXCLUDING_DB | {"db": SERVER_DATA_DIR / "db"}).items())
)

# "Explicit is better than implicit." - PEP 20
# Do not glob the template directories. Use these definitions.
TEMPLATE_SYSTEMD_UNITS_RESOURCE_PATH = "templates/config"
TEMPLATE_SYSTEMD_UNITS_FILENAMES = (
    f"{SERVER_SOFTWARE_PACKAGE}.network",
    f"{SERVER_SOFTWARE_PACKAGE}-app.container",
    f"{SERVER_SOFTWARE_PACKAGE}-celery-worker.container",
    f"{SERVER_SOFTWARE_PACKAGE}-db.container",
    f"{SERVER_SOFTWARE_PACKAGE}-redis.container",
    f"{SERVER_SOFTWARE_PACKAGE}-server.container",
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

SYSTEMD_GENERATED_SERVICES_DIR = os.environ.get("XDG_RUNTIME_DIR")
if SYSTEMD_GENERATED_SERVICES_DIR:
    SYSTEMD_GENERATED_SERVICES_DIR = (
        pathlib.Path(SYSTEMD_GENERATED_SERVICES_DIR) / "systemd/generator"
    )

SYSTEMD_SERVICE_FILENAMES = (
    f"{SERVER_SOFTWARE_PACKAGE}-app.service",
    f"{SERVER_SOFTWARE_PACKAGE}-celery-worker.service",
    f"{SERVER_SOFTWARE_PACKAGE}-db.service",
    f"{SERVER_SOFTWARE_PACKAGE}-network.service",
    f"{SERVER_SOFTWARE_PACKAGE}-redis.service",
    f"{SERVER_SOFTWARE_PACKAGE}-server.service",
)

# System commands commonly run
SYSTEMCTL_USER_RESET_FAILED_CMD = ["systemctl", "--user", "reset-failed"]
SYSTEMCTL_USER_DAEMON_RELOAD_CMD = ["systemctl", "--user", "daemon-reload"]
SYSTEMCTL_USER_LIST_QUIPUCORDS_APP = [
    "systemctl",
    "-q",
    "--user",
    "list-unit-files",
    f"{SERVER_SOFTWARE_PACKAGE}-app.service",
]
SYSTEMCTL_USER_STOP_QUIPUCORDS_APP = [
    "systemctl",
    "--user",
    "stop",
    f"{SERVER_SOFTWARE_PACKAGE}-app",
]
SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK = [
    "systemctl",
    "--user",
    "stop",
    f"{SERVER_SOFTWARE_PACKAGE}-network",
]

# podman secrets we use
QUIPUCORDS_SECRETS = {
    "db": f"{SERVER_SOFTWARE_PACKAGE}-db-password",
    "encryption": f"{SERVER_SOFTWARE_PACKAGE}-encryption-secret-key",
    "redis": f"{SERVER_SOFTWARE_PACKAGE}-redis-password",
    "server": f"{SERVER_SOFTWARE_PACKAGE}-server-password",
    "session": f"{SERVER_SOFTWARE_PACKAGE}-session-secret-key",
}

QUIPUCORDS_SECRET_KEYS = QUIPUCORDS_SECRETS.values()


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
