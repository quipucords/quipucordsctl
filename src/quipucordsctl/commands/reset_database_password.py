"""Reset the database password."""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings, shell_utils

logger = logging.getLogger(__name__)
DATABASE_PASSWORD_PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["db"]  # noqa: S105
DATABASE_PASSWORD_ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}DBMS_PASSWORD"
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


def confirm_replace_existing_secret() -> bool:
    """Confirm that the user wants to replace an existing secret."""
    logger.warning(
        _(
            "The database password already exists. "
            "Resetting the database password to a new value "
            "may result in data loss if you have already installed "
            "and run %(SERVER_SOFTWARE_NAME)s on this system."
        ),
        {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
    )
    return shell_utils.confirm(
        _("Are you sure you want to replace the existing database password? [y/n] ")
    )


def confirm_manual_reset() -> bool:
    """Confirm that the user wants to manually set a value into this secret."""
    logger.warning(
        _(
            "You should only manually reset the database password if you "
            "understand how it it used and you are addressing a specific issue. "
            "We strongly recommend using the automatically generated database "
            "password instead of manually entering one."
        )
    )
    return shell_utils.confirm(
        _("Are you sure you want to manually reset the database password? [y/n] ")
    )


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
    should_replace = podman_utils.secret_exists(DATABASE_PASSWORD_PODMAN_SECRET_NAME)
    if should_replace and not confirm_replace_existing_secret():
        return False

    if getattr(args, "prompt", False):
        if not confirm_manual_reset():
            return False
        if not (
            new_secret := secrets.prompt_secret(
                _("database password"), min_length=DATABASE_PASSWORD_MIN_LENGTH
            )
        ):
            logger.error(_("The database password was not updated."))
            return False
    else:
        new_secret, invalid = secrets.read_from_env(
            DATABASE_PASSWORD_ENV_VAR_NAME,
            _("database password"),
            min_length=DATABASE_PASSWORD_MIN_LENGTH,
        )
        if invalid or (new_secret and not confirm_manual_reset()):
            # Early return because env var was found but failed checks.
            # Or valid env var found and user declined to use it.
            return False

    if not new_secret:
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
