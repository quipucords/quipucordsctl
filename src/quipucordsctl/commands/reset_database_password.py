"""Reset the database password."""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings, shell_utils

logger = logging.getLogger(__name__)
DATABASE_PASSWORD_PODMAN_SECRET_NAME = "quipucords-db-password"  # noqa: S105
DATABASE_PASSWORD_MIN_LENGTH = 16


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the database password.")


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        help=_(
            "Prompt for custom database password "
            "(default: no prompt, generate a random value)"
        ),
    )


def is_set() -> bool:
    """Check if the database password is already set."""
    return podman_utils.secret_exists(DATABASE_PASSWORD_PODMAN_SECRET_NAME)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the database password.

    * If secret already exists, warn and confirm before proceeding.
    * If "--prompt" was set, warn and confirm before proceeding.
    * Prompt for new value or generate a value randomly.
    * If secret already exists, delete it.
    * Create new secret.
    * Return True if everything succeeds, or False if user declines any prompt.
    """
    if should_replace := podman_utils.secret_exists(
        DATABASE_PASSWORD_PODMAN_SECRET_NAME
    ):
        logger.warning(
            _(
                "The database password already exists. "
                "Resetting the database password to a new value "
                "may result in data loss if you have already installed "
                "and run %(SERVER_SOFTWARE_NAME)s on this system."
            ),
            {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
        )
        if not shell_utils.confirm(
            _("Are you sure you want to replace the existing database password? [y/n] ")
        ):
            return False
    if getattr(args, "prompt", False):
        logger.warning(
            _(
                "You should only manually reset the database password if you "
                "understand how it it used and you are addressing a specific issue. "
                "We strongly recommend using the automatically generated database "
                "password instead of manually entering one."
            )
        )
        if not shell_utils.confirm(
            _("Are you sure you want to manually reset the database password? [y/n] ")
        ):
            return False
        if not (
            new_secret := secrets.prompt_secret(
                _("database password"), min_length=DATABASE_PASSWORD_MIN_LENGTH
            )
        ):
            logger.error(_("The database password was not updated."))
            return False
    else:
        new_secret = secrets.generate_random_secret(DATABASE_PASSWORD_MIN_LENGTH)
        logger.info(
            _(
                "New value for podman secret %(PODMAN_SECRET_NAME)s "
                "was randomly generated."
            ),
            {"PODMAN_SECRET_NAME": DATABASE_PASSWORD_PODMAN_SECRET_NAME},
        )
    if not podman_utils.set_secret(
        DATABASE_PASSWORD_PODMAN_SECRET_NAME, new_secret, should_replace
    ):
        logger.error(_("The database password was not updated."))
        return False
    logger.debug(_("The database password was successfully updated."))
    return True
