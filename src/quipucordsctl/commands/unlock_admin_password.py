"""
Unlock the admin login after too many failed login attempts.

The server locks an account out after repeated failed logins. Clearing that
lockout is separate from resetting the password itself, because a user who
knows their password can still be locked out, and a user who resets their
password is still locked out until the lockout is cleared.

The server locks out by username and by source address independently, so a
lockout the admin earned from one address may also have blocked that address.
We clear only the admin's username records. If other accounts' failed logins
locked the same address, the admin stays locked out from it until that expires;
clearing it here would throw away protection against an attack in progress.
"""

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import argparse_utils, podman_utils, settings, systemctl_utils

logger = logging.getLogger(__name__)

PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["username"]

SERVER_NOT_RUNNING_MESSAGE = _(
    textwrap.dedent(
        """
        %(server_software_name)s is not running. Login lockouts are stored in the database, which is only reachable while the server is running. Please start the server and try again:

            %(program_name)s start
        """  # noqa: E501 line-too-long
    ).strip()
)

NO_ADMIN_USERNAME_MESSAGE = _(
    textwrap.dedent(
        """
        Could not read the admin login username from the '%(secret_name)s' podman secret, so there is no account to unlock. Please set the username and try again:

            %(program_name)s reset_admin_username
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
            to the admin account after too many failed login attempts.
            Run the `%(command_name)s` command if you are locked out and cannot log in
            from your web browser or CLI, even with the correct password.
            This command requires the server to be running because the lockout records
            are stored in the server's database.
            Only the admin account is unlocked; lockouts for other accounts and for
            addresses that other accounts' failed logins blocked are left in place.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
    }


def run(args: argparse.Namespace) -> bool:
    """
    Clear the admin account's login lockout on the server.

    Requires the server container to be running so that the management command
    can reach the database where the lockout records live. The container cannot
    start without the admin username secret, so reading it here should always
    succeed, but we check anyway rather than unlock the wrong account.

    Only the admin's own lockout is cleared. Other accounts keep their lockouts,
    and so does any address-based lockout that other accounts' failed logins
    earned, because that protection is not ours to discard.
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

    admin_username = podman_utils.get_secret_value(PODMAN_SECRET_NAME)
    if not admin_username or not admin_username.strip():
        logger.error(
            NO_ADMIN_USERNAME_MESSAGE
            % {
                "secret_name": PODMAN_SECRET_NAME,
                "program_name": settings.PROGRAM_NAME,
            }
        )
        return False

    # "--" stops the management command's parser from reading a username that
    # happens to start with "-" as an option. Usernames are only checked for
    # being non-empty when they are set, so that is a reachable input.
    if not podman_utils.exec_in_container(
        settings.SERVER_CONTAINER_NAME,
        [*settings.SERVER_AXES_RESET_USERNAME_COMMAND, "--", admin_username],
    ):
        logger.error(_("Failed to clear the admin login lockout."))
        return False

    logger.info(_("The admin login lockout was successfully cleared."))
    if not settings.runtime.quiet:
        print(
            _("The admin login lockout was cleared. You may now try to log in again.")
        )
    return True
