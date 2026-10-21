"""Helper functions for inspecting the user running this program."""

import logging
import os
import pwd
import textwrap
from gettext import gettext as _

from quipucordsctl import settings

logger = logging.getLogger(__name__)

ROOT_UID = 0

RUNNING_AS_ROOT_MESSAGE = _(
    textwrap.dedent(
        """
        %(program_name)s must not be run as the root user.

        Run %(program_name)s without sudo, su, or any other means of becoming root.
        """
    ).strip()
)


class RunningAsRootError(Exception):
    """Exception raised when this program is running as the root user."""


def get_username(uid: int) -> str:
    """Get the account name for the given uid, falling back to the uid itself."""
    # Note that we deliberately do not use getpass.getuser() here, because it trusts
    # the LOGNAME/USER/LNAME/USERNAME environment variables before consulting the
    # passwd database, and those variables are trivial for the user to change.
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def is_root() -> bool:
    """Return True if this program is running as the root user."""
    # Check both the real and the effective uid. sudo, su, sudo su, a direct root
    # login via ssh, `machinectl shell`, and `systemd-run --pty` all set both to 0,
    # but checking both also catches a setuid-root executable (real uid is not 0)
    # and a root process that has dropped only its effective uid.
    return ROOT_UID in (os.getuid(), os.geteuid())


def describe_current_user() -> str:
    """Describe the user running this program, for diagnostic output."""
    uid, euid = os.getuid(), os.geteuid()
    if uid == euid:
        return _("%(username)s (uid %(uid)d)") % {
            "username": get_username(uid),
            "uid": uid,
        }
    return _(
        "%(username)s (uid %(uid)d), effectively %(effective_username)s (euid %(euid)d)"
    ) % {
        "username": get_username(uid),
        "uid": uid,
        "effective_username": get_username(euid),
        "euid": euid,
    }


def ensure_not_root() -> None:
    """Ensure this program is not running as the root user."""
    logger.debug(_("Ensuring this program is not running as root."))
    if is_root():
        raise RunningAsRootError(
            RUNNING_AS_ROOT_MESSAGE % {"program_name": settings.PROGRAM_NAME}
        )
