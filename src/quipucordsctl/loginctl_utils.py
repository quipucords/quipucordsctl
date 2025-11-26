"""loginctl helper functions."""

import getpass
import logging
import subprocess
from gettext import gettext as _

from quipucordsctl import shell_utils

logger = logging.getLogger(__name__)


def is_linger_enabled(username):
    """Determine if Linger is enabled for a user."""
    cmd = ["loginctl", "show-user", username, "--property=Linger"]
    cmd_result, __, exit_code = shell_utils.run_command(cmd)
    if exit_code == 0:
        return True if cmd_result.strip().split("=")[1] == "yes" else False
    return False


def check_linger():
    """Check if Linger is enabled for the current user."""
    username = getpass.getuser()
    try:
        if is_linger_enabled(username):
            logger.info(
                _("Linger is enabled for user '%(username)s'"),
                {"username": username},
            )
        return True
    except subprocess.CalledProcessError:
        logger.error(
            _(
                "loginctl failed unexpectedly, unable to check Linger"
                " for user '%(username)s'. Please check logs."
            ),
            {"username": username},
        )
        return False


def enable_linger(no_linger: bool):
    """Enable Linger for the current user."""
    username = getpass.getuser()
    if no_linger:
        logger.info(
            _("Linger will not be enabled for user '%(username)s'."),
            {"username": username},
        )
        return True
    try:
        if is_linger_enabled(username):
            logger.info(
                _("Linger is enabled for user '%(username)s'"),
                {"username": username},
            )
            return True
        logger.info(
            _("Enabling Linger for user '%(username)s'"),
            {"username": username},
        )
        cmd = ["loginctl", "enable-linger", username]
        shell_utils.run_command(cmd)
        return True
    except subprocess.CalledProcessError:
        logger.error(
            _(
                "loginctl failed unexpectedly, unable to enable Linger"
                " for user '%(username)s'. Please check logs."
            ),
            {"username": username},
        )
        return False
