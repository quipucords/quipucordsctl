"""Logic for the "install" command."""

import itertools
import logging
import shutil

from .. import settings, shell_utils
from . import reset_django_secret, reset_server_password

DATA_DIRS = ("data", "db", "log", "sshkeys")
SYSTEMCTL_USER_RESET_FAILED_CMD = ["systemctl", "--user", "reset-failed"]
SYSTEMCTL_USER_DAEMON_RELOAD_CMD = ["systemctl", "--user", "daemon-reload"]

logger = logging.getLogger(__name__)


def mkdirs():
    """Ensure required data and config directories exist."""
    for data_dir in DATA_DIRS:
        dir_path = settings.SERVER_DATA_DIR / data_dir
        logger.debug("Ensuring data directory exists: %s", dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"{dir_path} exists but is not a directory.")

    for config_dir in (settings.SERVER_ENV_DIR, settings.SYSTEMD_UNITS_DIR):
        logger.debug("Ensuring config directory exists: %s", config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        if not config_dir.is_dir():
            raise NotADirectoryError(f"{config_dir} exists but is not a directory.")


def write_config_files(override_conf_dir: str | None = None):
    """Generate and write to disk all systemd unit and env files for the server."""
    logger.info("Generating config files")
    mkdirs()

    if override_conf_dir:
        # TODO support override files
        raise NotImplementedError
    systemd_templates = list(
        itertools.chain(
            settings.SYSTEMD_UNITS_TEMPLATES_DIR.glob("*.network"),
            settings.SYSTEMD_UNITS_TEMPLATES_DIR.glob("*.container"),
        )
    )
    for template_path in systemd_templates:
        # TODO merge with override files, maybe using configparser.
        destination = settings.SYSTEMD_UNITS_DIR / template_path.name
        logger.debug(f"Copying {template_path} to {destination}")
        shutil.copy(template_path, destination)

    env_templates = settings.ENV_TEMPLATES_DIR.glob("*.env")
    for template_path in env_templates:
        # TODO merge with override files, maybe using configparser.
        destination = settings.SERVER_ENV_DIR / template_path.name
        logger.debug(f"Copying {template_path} to {destination}")
        shutil.copy(template_path, destination)


def systemctl_reload():
    """Reload systemctl service to recognize new/updated units."""
    logger.info(
        "Reloading systemctl to recognize %s units",
        settings.SERVER_SOFTWARE_NAME,
    )
    shell_utils.run_command(SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(SYSTEMCTL_USER_DAEMON_RELOAD_CMD)


def run(override_conf_dir: str | None = None):
    """Install the server, ensuring requirements are met."""
    logger.info("Starting install command")
    if override_conf_dir:
        raise NotImplementedError

    if not reset_server_password.server_password_is_set():
        reset_server_password.run()
    if not reset_django_secret.django_secret_is_set():
        reset_django_secret.run()

    write_config_files()
    systemctl_reload()
