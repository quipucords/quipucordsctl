"""Install the server."""

import argparse
import itertools
import logging
import shutil
from gettext import gettext as _

from quipucordsctl import settings, shell_utils
from quipucordsctl.commands import (
    reset_admin_password,
    reset_encryption_secret,
    reset_session_secret,
)

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
    dir_paths = [
        settings.SERVER_ENV_DIR,
        settings.SYSTEMD_UNITS_DIR,
    ] + list(settings.SERVER_DATA_SUBDIRS.values())
    for dir_path in dir_paths:
        logger.debug(
            _("Ensuring directory exists: %(dir_path)s"),
            {"dir_path": dir_path},
        )
        dir_path.mkdir(parents=True, exist_ok=True)
        if not dir_path.is_dir():
            raise NotADirectoryError(
                _("%(dir_path)s exists but is not a directory."), {"dir_path": dir_path}
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


def run(args: argparse.Namespace) -> bool:
    """Install the server, ensuring requirements are met."""
    logger.info("Starting install command")
    if args.override_conf_dir:
        raise NotImplementedError

    if (
        not reset_encryption_secret.encryption_secret_is_set()
        and not reset_encryption_secret.run(args)
    ):
        logger.error(_("The install command failed to reset encryption secret."))
        return False
    if (
        not reset_session_secret.session_secret_is_set()
        and not reset_session_secret.run(args)
    ):
        logger.error(_("The install command failed to reset session secret."))
        return False
    if (
        not reset_admin_password.admin_password_is_set()
        and not reset_admin_password.run(args)
    ):
        logger.error(_("The install command failed to reset admin password."))
        return False

    write_config_files()
    systemctl_reload()
    return True
