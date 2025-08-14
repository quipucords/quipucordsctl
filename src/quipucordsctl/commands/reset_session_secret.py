"""
Reset the session secret key.

The session secret key is used for short-lived cryptographic signing
of session data and related tokens.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, shell_utils

logger = logging.getLogger(__name__)
SESSION_SECRET_PODMAN_SECRET_NAME = "quipucords-session-secret-key"  # noqa: S105
SECRET_MIN_LENGTH = 64


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the session secret key.")


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        help=_(
            "Prompt for custom session secret key "
            "(default: no prompt, generate a random value)"
        ),
    )


def session_secret_is_set() -> bool:
    """Check if the session secret key is already set."""
    return podman_utils.secret_exists(SESSION_SECRET_PODMAN_SECRET_NAME)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the server session secret key.

    * Prompt for new value or generate a value randomly.
    * If secret already exists, delete it.
    * Create new secret.
    * Return True if everything succeeds, or False if user declines any prompt.
    """
    if args.prompt:
        logger.warning(
            _(
                "You should only manually reset the session secret key if you "
                "understand how it it used and you are addressing a specific issue. "
                "We strongly recommend using the automatically generated session "
                "secret key instead of manually entering one."
            )
        )
        if not shell_utils.confirm(
            _("Are you sure you want to manually reset the session secret key? [y/n] ")
        ):
            return False
        if not (
            new_secret := secrets.prompt_secret(
                _("session secret key"), min_length=SECRET_MIN_LENGTH
            )
        ):
            logger.error(_("The session secret key was not updated."))
            return False
    else:
        new_secret = secrets.generate_random_secret(SECRET_MIN_LENGTH)
        logger.info(
            _(
                "New value for podman secret %(PODMAN_SECRET_NAME)s "
                "was randomly generated."
            ),
            {"PODMAN_SECRET_NAME": SESSION_SECRET_PODMAN_SECRET_NAME},
        )
    if not podman_utils.set_secret(SESSION_SECRET_PODMAN_SECRET_NAME, new_secret):
        logger.error(_("The session secret key was not updated."))
        return False
    logger.debug(_("The session secret key was successfully updated."))
    return True
