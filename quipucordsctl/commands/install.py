"""Install the server."""

import argparse
import itertools
import logging
import shutil
from gettext import gettext as _

from quipucordsctl import settings, shell_utils
from quipucordsctl.commands import reset_admin_password, reset_session_secret

DATA_DIRS = ("data", "db", "log", "sshkeys")
SYSTEMCTL_USER_RESET_FAILED_CMD = ["systemctl", "--user", "reset-failed"]
SYSTEMCTL_USER_DAEMON_RELOAD_CMD = ["systemctl", "--user", "daemon-reload"]

logger = logging.getLogger(__name__)


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Install the %(server_software_name)s server.") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def mkdirs():
    """Ensure required data and config directories exist."""
    for data_dir in DATA_DIRS:
        dir_path = settings.SERVER_DATA_DIR / data_dir
        logger.debug(
            _("Ensuring data directory exists: %(dir_path)s"),
            {"dir_path": dir_path},
        )
        dir_path.mkdir(parents=True, exist_ok=True)
        if not dir_path.is_dir():
            raise NotADirectoryError(
                _("%(dir_path)s exists but is not a directory."), {"dir_path": dir_path}
            )

    for config_dir in (settings.SERVER_ENV_DIR, settings.SYSTEMD_UNITS_DIR):
        logger.debug(
            _("Ensuring config directory exists: %(config_dir)s"),
            {"config_dir": config_dir},
        )
        config_dir.mkdir(parents=True, exist_ok=True)
        if not config_dir.is_dir():
            raise NotADirectoryError(
                _("%(config_dir)s exists but is not a directory."),
                {"config_dir": config_dir},
            )


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
        logger.debug(
            _("Copying %(template_path)s to %(destination)s"),
            {"template_path": template_path, "destination": destination},
        )
        shutil.copy(template_path, destination)

    env_templates = settings.ENV_TEMPLATES_DIR.glob("*.env")
    for template_path in env_templates:
        # TODO merge with override files, maybe using configparser.
        destination = settings.SERVER_ENV_DIR / template_path.name
        logger.debug(
            _("Copying %(template_path)s to %(destination)s"),
            {"template_path": template_path, "destination": destination},
        )
        shutil.copy(template_path, destination)


def systemctl_reload():
    """Reload systemctl service to recognize new/updated units."""
    logger.info(
        _("Reloading systemctl to recognize %(server_software_name)s units"),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    shell_utils.run_command(SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(SYSTEMCTL_USER_DAEMON_RELOAD_CMD)


def run(args: argparse.Namespace) -> None:
    """Install the server, ensuring requirements are met."""
    logger.info("Starting install command")
    if args.override_conf_dir:
        raise NotImplementedError

    if not reset_admin_password.admin_password_is_set():
        reset_admin_password.run(args)
    if not reset_session_secret.application_secret_is_set():
        reset_session_secret.run(args)

    write_config_files()
    systemctl_reload()
