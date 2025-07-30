"""Reset the Django secret key."""
# TODO Should this command also conditionally restart the server?

import argparse
import getpass
import logging
import re
import secrets
from gettext import gettext as _

from .. import settings, shell_utils

logger = logging.getLogger(__name__)
PODMAN_SECRET_NAME = "quipucords-server-password"  # noqa: S105
SECRET_MIN_LENGTH = 64


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the server's internal secret encryption key.")


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        help=_(
            "Prompt for custom secret key (default: no prompt, generate a random value)"
        ),
    )


def application_secret_is_set() -> bool:
    """Check if the application/Django secret key is already set."""
    # TODO `podman secret exists quipucords-django-secret-key`
    return False


def check_secret(new_secret: str, confirm_secret: str) -> bool:
    """Check if the new secret inputs are sufficient to set."""
    if new_secret != confirm_secret:
        logger.error(_("Your application secret inputs do not match."))
        return False
    if len(new_secret) < SECRET_MIN_LENGTH:
        logger.error(
            _(
                "Your application secret must be at least "
                "%(SECRET_MIN_LENGTH)s characters long."
            ),
            {"SECRET_MIN_LENGTH": SECRET_MIN_LENGTH},
        )
        return False
    if not re.search("[0-9]", new_secret):
        logger.error(_("Your application secret must contain a number."))
        return False
    if not re.search("[a-zA-Z]", new_secret):
        logger.error(_("Your application secret must contain a letter."))
        return False

    return True


def prompt_secret() -> str | None:
    """Prompt the user to enter a new application secret key."""
    logger.warning(
        _(
            "New application secret key must be at least "
            "%(SECRET_MIN_LENGTH)s characters long."
        ),
        {"SECRET_MIN_LENGTH": SECRET_MIN_LENGTH},
    )
    new_secret = getpass.getpass(_("Enter new server application secret key: "))
    confirm_secret = getpass.getpass(_("Confirm new server application secret key: "))
    if not check_secret(new_secret, confirm_secret):
        logger.error(_("Application secret key was not updated."))
        return None
    return new_secret


def generate_random_secret() -> str:
    """Generate a random application secret key."""
    return secrets.token_urlsafe(SECRET_MIN_LENGTH)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the server application secret key.

    * If secret already exists, warn and confirm before proceeding.
    * If "--prompt" was set, warn and confirm before proceeding.
    * Prompt for new value or generate a value randomly.
    * If secret already exists, delete it.
    * Create new secret.
    * Return True if everything succeeds, or False if user declines any prompt.
    """
    with shell_utils.get_podman_client() as podman_client:
        if remove := podman_client.secrets.exists(PODMAN_SECRET_NAME):
            logger.warning(
                _(
                    "The application secret key already exists. "
                    "Resetting the application secret key to a new value "
                    "may result in data loss if you have already installed "
                    "and run %(SERVER_SOFTWARE_NAME)s on this system."
                ),
                {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
            )
            if not shell_utils.confirm(
                _(
                    "Are you sure you want to replace "
                    "the existing application secret key? [y/n] "
                )
            ):
                return False
        if args.prompt:
            logger.warning(
                _(
                    "You should only manually reset the application secret key "
                    "if you understand how it it used and you are addressing a "
                    "specific issue. We strongly recommend using the automatically "
                    "generated application secret key instead of manually entering "
                    "one."
                ),
                {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
            )
            if not shell_utils.confirm(
                _(
                    "Are you sure you want to manually reset "
                    "the application secret key? [y/n] "
                )
            ) or not (new_secret := prompt_secret()):
                return False
        else:
            new_secret = generate_random_secret()
            logger.info(
                _(
                    "New value for podman secret %(PODMAN_SECRET_NAME)s "
                    "was randomly generated."
                ),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
        if remove:
            podman_client.secrets.remove(PODMAN_SECRET_NAME)
            logger.info(
                _("Old podman secret %(PODMAN_SECRET_NAME)s was removed."),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
        podman_client.secrets.create(PODMAN_SECRET_NAME, new_secret)
    return True
