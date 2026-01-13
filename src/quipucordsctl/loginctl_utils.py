"""loginctl helper functions."""

import getpass
import logging
import subprocess
from gettext import gettext as _

from quipucordsctl import shell_utils

logger = logging.getLogger(__name__)


def is_linger_enabled(username):
    """Check if the 'Linger' property is enabled for the given user."""
    cmd_env = {
        "LANG": "C",
        "LC_ALL": "C",
    }
    cmd = ["loginctl", "show-user", username, "--property=Linger"]
    cmd_result, __, exit_code = shell_utils.run_command(cmd, env=cmd_env)
    return cmd_result.strip().split("=")[1] == "yes" if exit_code == 0 else False


def check_linger():
    """Check if the 'Linger' property is enabled for the current user."""
    username = getpass.getuser()
    try:
        if is_linger_enabled(username):
            logger.info(
                _("'Linger' is enabled for user '%(username)s'"),
                {"username": username},
            )
        return True
    except subprocess.CalledProcessError:
        logger.error(
            _(
                "loginctl failed unexpectedly. Unable to check 'Linger' property "
                "for user '%(username)s'. Please check logs."
            ),
            {"username": username},
        )
        return False


def enable_linger(linger: bool):
    """Enable the 'Linger' property for the current user."""
    username = getpass.getuser()
    if not linger:
        logger.info(
            _("'Linger' will not be checked or enabled for user '%(username)s'."),
            {"username": username},
        )
        return True
    try:
        if is_linger_enabled(username):
            logger.info(
                _("'Linger' is enabled for user '%(username)s'"),
                {"username": username},
            )
            return True
        logger.info(
            _("Enabling 'Linger' for user '%(username)s'"),
            {"username": username},
        )
        cmd = ["loginctl", "enable-linger", username]
        shell_utils.run_command(cmd)
        return True
    except subprocess.CalledProcessError:
        logger.error(
            _(
                "loginctl failed unexpectedly. Failed to enable 'Linger' "
                "for user '%(username)s'. Please check logs."
            ),
            {"username": username},
        )
        return False
