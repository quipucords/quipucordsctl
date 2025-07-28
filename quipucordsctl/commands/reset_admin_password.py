"""Reset the server's login password."""

import argparse
import difflib
import getpass
import logging
import subprocess
from gettext import gettext as _

logger = logging.getLogger(__name__)
PODMAN_SECRET_NAME = "quipucords-server-password"  # noqa: S105
PASSWORD_MIN_LENGTH = 10
PASSWORD_BLOCKLIST = ["dscpassw0rd", "qpcpassw0rd"]
DEFAULT_USERNAME = "admin"
PASSWORD_USERNAME_MAX_SIMILARITY = 0.7


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the server's login password.")


def admin_password_is_set() -> bool:
    """Check if the admin password is already set."""
    # TODO `podman secret exists PODMAN_SECRET_NAME`
    # TODO Implement or delete this if we don't actually need it.
    return False


def check_password(new_password, confirm_password):
    """Check if the new password inputs are sufficient to set."""
    if new_password != confirm_password:
        logger.error(_("Your password inputs do not match."))
        return False
    if len(new_password) < PASSWORD_MIN_LENGTH:
        # mimic MinimumLengthValidator on the server
        logger.error(
            _(
                "Your password must be at least "
                "%(PASSWORD_MIN_LENGTH)s characters long."
            ),
            {"PASSWORD_MIN_LENGTH": PASSWORD_MIN_LENGTH},
        )
        return False
    if new_password.isdigit():
        # mimic NumericPasswordValidator on the server
        logger.error(_("Your password cannot be entirely numeric."))
        return False
    if new_password in PASSWORD_BLOCKLIST:
        # mimic CommonPasswordValidator on the server
        logger.error(_("Your password cannot be used because it is blocked."))
        return False
    if (
        difflib.SequenceMatcher(a=new_password, b=DEFAULT_USERNAME).quick_ratio()
        >= PASSWORD_USERNAME_MAX_SIMILARITY
    ):
        # mimic UserAttributeSimilarityValidator on the server
        # TODO Refactor this when we allow the user to set a custom login username.
        logger.error(_("Your password is too similar to your login username."))
        return False

    return True


def prompt_password() -> str | None:
    """Prompt the user to enter a new password."""
    new_password = getpass.getpass(_("Enter new server login password: "))
    confirm_password = getpass.getpass(_("Confirm new server login password: "))
    if not check_password(new_password, confirm_password):
        logger.error(_("Password was not updated."))
        return None
    return new_password


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Reset the server password."""
    if not (new_password := prompt_password()):
        return False

    command = [
        "podman",
        "secret",
        "create",
        "--replace",
        PODMAN_SECRET_NAME,
        "-",
    ]

    try:
        process = subprocess.Popen(  # noqa: S603
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=new_password)

        if process.returncode == 0:
            logger.info(
                _(
                    "podman secret '%(PODMAN_SECRET_NAME)s' "
                    "created/replaced successfully."
                ),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
            logger.debug("podman stdout:")
            logger.debug(stdout)
            return True
        else:
            logger.error(
                _("Failed to create podman secret '%(PODMAN_SECRET_NAME)s'."),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
            # TODO Should we *always* show podman's stderr, or gate it behind -vv?
            logger.debug("podman stderr:")
            logger.debug(stderr)
            return False

    except FileNotFoundError:
        logger.error(
            _(
                "'%(command_name)s' command not found. "
                "Please ensure %(command_name)s is installed and in your PATH."
            ),
            {"command_name": "podman"},
        )
        return False
    except Exception as e:  # noqa: BLE001
        logger.error(_("An unexpected error occurred: %(error)s"), {"error": e})
        return False

    # TODO Should this command also conditionally restart the server?
