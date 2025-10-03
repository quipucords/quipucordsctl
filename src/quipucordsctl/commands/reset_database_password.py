"""
Reset the database password.

The database password is used only for communicating with the local database.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings

logger = logging.getLogger(__name__)
PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["db"]  # noqa: S105
ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}DBMS_PASSWORD"
MIN_LENGTH = 16
REQUIREMENTS = {"min_length": MIN_LENGTH}


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
    return podman_utils.secret_exists(PODMAN_SECRET_NAME)


reset_secret_messages = secrets.ResetSecretMessages(
    manual_reset_warning=_(
        "You should only manually reset the database password if you "
        "understand how it is used, and you are addressing a specific issue. "
        "We strongly recommend using the automatically generated value for "
        "the database password instead of manually entering one."
    ),
    manual_reset_question=_(
        "Are you sure you want to manually set a custom database password?"
    ),
    replace_existing_warning=_(
        "The database password has already been set. "
        "Resetting the database password to a new value "
        "may result in data loss if you have already installed "
        "and run %(SERVER_SOFTWARE_NAME)s on this system."
    )
    % {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
    replace_existing_question=_(
        "Are you sure you want to replace the existing database password?"
    ),
)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the database password.

    Value is random by default, but allow manual input via '--prompt' or env var.

    Returns True if everything succeeded, else False because some input validation
    failed or the user declined a confirmation prompt.
    """
    already_exists = podman_utils.secret_exists(PODMAN_SECRET_NAME)
    new_secret = secrets.get_new_secret_value(
        podman_secret_name=PODMAN_SECRET_NAME,
        messages=reset_secret_messages,
        must_confirm_replace_existing=already_exists,
        must_confirm_allow_nonrandom=True,
        must_prompt_interactive_input=getattr(args, "prompt", False),
        may_prompt_interactive_input=getattr(args, "prompt", False),
        env_var_name=ENV_VAR_NAME,
        check_requirements=REQUIREMENTS,
    )

    if new_secret and podman_utils.set_secret(
        PODMAN_SECRET_NAME, new_secret, already_exists
    ):
        logger.debug(_("The database password was successfully updated."))
        return True

    logger.error(_("The database password was not updated."))
    return False
