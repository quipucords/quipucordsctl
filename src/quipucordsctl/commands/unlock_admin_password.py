"""
Unlock the admin login after too many failed login attempts.

The server locks an account out after repeated failed logins. Clearing that
lockout is separate from resetting the password itself, because a user who
knows their password can still be locked out, and a user who resets their
password is still locked out until the lockout is cleared.
"""

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import argparse_utils, podman_utils, settings, systemctl_utils

logger = logging.getLogger(__name__)

SERVER_NOT_RUNNING_MESSAGE = _(
    textwrap.dedent(
        """
        %(server_software_name)s is not running. Login lockouts are stored in the database, which is only reachable while the server is running. Please start the server and try again:

            %(program_name)s start
        """  # noqa: E501 line-too-long
    ).strip()
)


def get_display_group() -> argparse_utils.DisplayGroups:
    """Get the group identifier for displaying this command in CLI help text."""
    return argparse_utils.DisplayGroups.CONFIG


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Unlock the admin login after too many failed attempts")


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Clear the login lockout that the %(server_software_name)s server applies
            after too many failed login attempts.
            Run the `%(command_name)s` command if you are locked out and cannot log in
            from your web browser or CLI, even with the correct password.
            This command requires the server to be running because the lockout records
            are stored in the server's database.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
    }


def run(args: argparse.Namespace) -> bool:
    """
    Clear all login lockouts on the server.

    Requires the server container to be running so that the management command
    can reach the database where the lockout records live.
    """
    systemctl_utils.ensure_systemd_user_session()
    podman_utils.ensure_podman_socket()

    if not podman_utils.container_is_running(settings.SERVER_CONTAINER_NAME):
        logger.error(
            SERVER_NOT_RUNNING_MESSAGE
            % {
                "server_software_name": settings.SERVER_SOFTWARE_NAME,
                "program_name": settings.PROGRAM_NAME,
            }
        )
        return False

    if not podman_utils.exec_in_container(
        settings.SERVER_CONTAINER_NAME, settings.SERVER_AXES_RESET_COMMAND
    ):
        logger.error(_("Failed to clear the login lockouts."))
        return False

    logger.info(_("Login lockouts were successfully cleared."))
    if not settings.runtime.quiet:
        print(_("Login lockouts were cleared. You may now attempt to log in again."))
    return True
