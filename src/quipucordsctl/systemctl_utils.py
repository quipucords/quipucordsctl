"""Shared systemctl helper functions."""

import logging
from gettext import gettext as _

from quipucordsctl import settings, shell_utils

logger = logging.getLogger(__name__)


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
