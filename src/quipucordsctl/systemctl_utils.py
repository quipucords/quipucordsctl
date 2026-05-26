"""Shared systemctl helper functions."""

import logging
import os
import subprocess
import textwrap
import time
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


def is_service_installed() -> bool:
    """Return True if the quipucords-app systemd unit file is present."""
    __, __, exit_code = shell_utils.run_command(
        settings.SYSTEMCTL_USER_LIST_QUIPUCORDS_APP, raise_error=False
    )
    return exit_code == 0


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


_START_FAILURE_GUIDANCE = textwrap.dedent(
    _(
        """
        %(server_software_name)s failed to start. Check the journal for errors:

            journalctl --user -u %(server_software_package)s-app

        You may also run '%(program_name)s check' for a system health check.
        """
    ).strip()
)


def _log_start_failure_details() -> None:
    """Print service status and log user guidance after a failed start."""
    stdout, __, __ = shell_utils.run_command(
        settings.SYSTEMCTL_USER_STATUS_QUIPUCORDS_APP,
        raise_error=False,
    )
    if stdout and not settings.runtime.quiet:
        print(stdout)
    logger.error(
        _(_START_FAILURE_GUIDANCE)
        % {
            "server_software_name": settings.SERVER_SOFTWARE_NAME,
            "server_software_package": settings.SERVER_SOFTWARE_PACKAGE,
            "program_name": settings.PROGRAM_NAME,
        }
    )


def start_service() -> bool:
    """Start quipucords-app and wait until the service becomes active."""
    logger.info(
        _("Starting the %(server_software_name)s server."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    try:
        shell_utils.run_command(settings.SYSTEMCTL_USER_START_QUIPUCORDS_APP)
    except subprocess.CalledProcessError:
        logger.error(
            _("Failed to issue start command for %(server_software_name)s."),
            {"server_software_name": settings.SERVER_SOFTWARE_NAME},
        )
        _log_start_failure_details()
        return False

    deadline = time.monotonic() + settings.DEFAULT_SERVICE_START_WAIT_TIMEOUT
    while time.monotonic() < deadline:
        if check_service_running():
            logger.info(
                _("%(server_software_name)s server is active."),
                {"server_software_name": settings.SERVER_SOFTWARE_NAME},
            )
            return True
        __, __, failed_exit = shell_utils.run_command(
            settings.SYSTEMCTL_USER_IS_FAILED_QUIPUCORDS_APP,
            raise_error=False,
        )
        if failed_exit == 0:
            break
        time.sleep(5)

    _log_start_failure_details()
    return False
