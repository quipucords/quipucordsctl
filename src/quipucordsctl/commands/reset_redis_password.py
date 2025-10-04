"""
Reset the Redis password.

The Redis password is used for short-lived cryptographic signing
of session data and related tokens.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings, shell_utils

logger = logging.getLogger(__name__)
REDIS_PASSWORD_PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["redis"]  # noqa: S105
SECRET_MIN_LENGTH = 64


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the Redis password.")


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        help=_(
            "Prompt for custom Redis password "
            "(default: no prompt, generate a random value)"
        ),
    )


def is_set() -> bool:
    """Check if the Redis password is already set."""
    return podman_utils.secret_exists(REDIS_PASSWORD_PODMAN_SECRET_NAME)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the server Redis password.

    * Prompt for new value or generate a value randomly.
    * If secret already exists, delete it.
    * Create new secret.
    * Return True if everything succeeds, or False if user declines any prompt.
    """
    if getattr(args, "prompt", False):
        logger.warning(
            _(
                "You should only manually reset the Redis password if you "
                "understand how it it used and you are addressing a specific issue. "
                "We strongly recommend using the automatically generated Redis "
                "password instead of manually entering one."
            )
        )
        if not shell_utils.confirm(
            _("Are you sure you want to manually reset the Redis password? [y/n] ")
        ):
            return False
        if not (
            new_secret := secrets.prompt_secret(
                _("Redis password"), min_length=SECRET_MIN_LENGTH
            )
        ):
            logger.error(_("The Redis password was not updated."))
            return False
    else:
        new_secret = secrets.generate_random_secret(SECRET_MIN_LENGTH)
        logger.info(
            _(
                "New value for podman secret %(PODMAN_SECRET_NAME)s "
                "was randomly generated."
            ),
            {"PODMAN_SECRET_NAME": REDIS_PASSWORD_PODMAN_SECRET_NAME},
        )
    if not podman_utils.set_secret(REDIS_PASSWORD_PODMAN_SECRET_NAME, new_secret):
        logger.error(_("The Redis password was not updated."))
        return False
    logger.debug(_("The Redis password was successfully updated."))
    return True
