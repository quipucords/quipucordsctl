"""
Reset the encryption secret key.

The encryption secret key is used to encrypt credentials in the database.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings, shell_utils

logger = logging.getLogger(__name__)
ENCRYPTION_SECRET_KEY_PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["encryption"]  # noqa: S105 E501
ENCRYPTION_SECRET_KEY_MIN_LENGTH = 64


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the encryption secret key.")


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        help=_(
            "Prompt for custom encryption secret key "
            "(default: no prompt, generate a random value)"
        ),
    )


def is_set() -> bool:
    """Check if the encryption secret key is already set."""
    return podman_utils.secret_exists(ENCRYPTION_SECRET_KEY_PODMAN_SECRET_NAME)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the server encryption secret key.

    * If secret already exists, warn and confirm before proceeding.
    * If "--prompt" was set, warn and confirm before proceeding.
    * Prompt for new value or generate a value randomly.
    * If secret already exists, delete it.
    * Create new secret.
    * Return True if everything succeeds, or False if user declines any prompt.
    """
    if should_replace := podman_utils.secret_exists(
        ENCRYPTION_SECRET_KEY_PODMAN_SECRET_NAME
    ):
        logger.warning(
            _(
                "The encryption secret key already exists. "
                "Resetting the encryption secret key to a new value "
                "may result in data loss if you have already installed "
                "and run %(SERVER_SOFTWARE_NAME)s on this system."
            ),
            {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
        )
        if not shell_utils.confirm(
            _(
                "Are you sure you want to replace "
                "the existing encryption secret key? [y/n] "
            )
        ):
            return False
    if getattr(args, "prompt", False):
        logger.warning(
            _(
                "You should only manually reset the encryption secret key "
                "if you understand how it it used and you are addressing a specific "
                "issue. We strongly recommend using the automatically generated "
                "encryption secret key instead of manually entering one."
            ),
            {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
        )
        if not shell_utils.confirm(
            _(
                "Are you sure you want to manually reset "
                "the encryption secret key? [y/n] "
            )
        ):
            return False
        if not (
            new_secret := secrets.prompt_secret(
                _("encryption secret key"),
                min_length=ENCRYPTION_SECRET_KEY_MIN_LENGTH,
            )
        ):
            logger.error(_("The encryption secret key was not updated."))
            return False
    else:
        new_secret = secrets.generate_random_secret(ENCRYPTION_SECRET_KEY_MIN_LENGTH)
        logger.info(
            _(
                "New value for podman secret %(PODMAN_SECRET_NAME)s "
                "was randomly generated."
            ),
            {"PODMAN_SECRET_NAME": ENCRYPTION_SECRET_KEY_PODMAN_SECRET_NAME},
        )
    if not podman_utils.set_secret(
        ENCRYPTION_SECRET_KEY_PODMAN_SECRET_NAME, new_secret, should_replace
    ):
        logger.error(_("The encryption secret key was not updated."))
        return False
    return True
