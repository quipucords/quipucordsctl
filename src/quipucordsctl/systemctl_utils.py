"""Shared systemctl helper functions."""

import logging
import os
from gettext import gettext as _

from quipucordsctl import settings, shell_utils

logger = logging.getLogger(__name__)


class NoSystemdUserSessionError(Exception):
    """Exception raised when there is no systemd user session."""


def ensure_systemd_user_session():
    """Ensure that systemd user session is enabled."""
    logger.debug(_("Ensuring systemd user session is enabled."))
    if not os.getenv("XDG_RUNTIME_DIR"):
        raise NoSystemdUserSessionError(
            _(
                "XDG_RUNTIME_DIR variable is not set. User systemd session will not "
                "work properly and you will encounter issues when trying to start "
                "%(server_software_name)s. If this is a remote machine, please SSH "
                "directly as the current user (instead of using sudo or su)."
            )
            % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
        )

    __, stderr, exit_code = shell_utils.run_command(
        settings.SYSTEMCTL_USER_IS_SYSTEM_RUNNING_CMD
    )
    logger.debug(stderr)

    if exit_code != 0:
        raise NoSystemdUserSessionError(
            _(
                "systemctl self-check reported problems. "
                "System is probably misconfigured and you are likely to encounter "
                "issues when trying to start %(server_software_name)s."
            )
            % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
        )


def stop_service() -> bool:
    """Stop the quipucords-app service if it's installed and running."""
    logger.info(
        _("Stopping the %(server_software_name)s server."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    __, __, exit_code = shell_utils.run_command(
        settings.SYSTEMCTL_USER_LIST_QUIPUCORDS_APP, raise_error=False
    )
    if exit_code == 0:
        try:
            shell_utils.run_command(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_APP)
            shell_utils.run_command(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK)
        except Exception as error:  # noqa: BLE001
            logger.error(
                _("Could not stop the %(server_software_name)s server."),
                {"server_software_name": settings.SERVER_SOFTWARE_NAME},
            )
            logger.debug(
                _("Error stopping %(server_software_name)s: %(error)s"),
                {
                    "server_software_name": settings.SERVER_SOFTWARE_NAME,
                    "error": error,
                },
            )
            return False
    return True


def reload_daemon() -> bool:
    """Reset systemctl failures and reload the daemon."""
    logger.info(_("Reloading the systemctl daemon."))
    shell_utils.run_command(settings.SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD)
    return True


def check_service_running() -> bool:
    """Check if quipucords-app service is currently running."""
    logger.debug(
        _("Checking if %(server_software_name)s service is active"),
        {
            "server_software_name": settings.SERVER_SOFTWARE_NAME,
        },
    )
    __, __, status_exit = shell_utils.run_command(
        [
            "systemctl",
            "-q",
            "--user",
            "is-active",
            f"{settings.SERVER_SOFTWARE_PACKAGE}-app.service",
        ],
        raise_error=False,
    )
    return status_exit == 0
