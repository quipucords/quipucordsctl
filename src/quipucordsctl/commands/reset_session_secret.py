"""
Reset the session secret key.

The session secret key is used for short-lived cryptographic signing
of session data and related tokens.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings

logger = logging.getLogger(__name__)
PODMAN_SECRET_NAME = "quipucords-session-secret-key"  # noqa: S105
ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}SESSION_SECRET_KEY"
MIN_LENGTH = 64
REQUIREMENTS = {"min_length": MIN_LENGTH}


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the session secret key.")


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            The `%(command_name)s` command resets the %(server_software_name)s
            session secret key. This secret key is used only by the
            %(server_software_name)s server internally to protect your session and
            the connection between your web browser or CLI and the
            %(server_software_name)s server, and as a user, you never need to use
            this secret key directly.
            The `%(command_name)s` command will try to use the value from
            the environment variable `%(env_var_name)s` if you have set one.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
        "env_var_name": ENV_VAR_NAME,
    }


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


def is_set() -> bool:
    """Check if the session secret key is already set."""
    return podman_utils.secret_exists(PODMAN_SECRET_NAME)


reset_secret_messages = secrets.ResetSecretMessages(
    manual_reset_warning=_(
        "You should only manually reset the session secret key if you "
        "understand how it is used, and you are addressing a specific issue. "
        "We strongly recommend using the automatically generated value for "
        "the session secret key instead of manually entering one."
    ),
    manual_reset_question=_(
        "Are you sure you want to manually set a custom session secret key?"
    ),
    replace_existing_warning=_(
        "The session secret key has already been set. "
        "Resetting the session secret key to a new value "
        "may result in data loss if you have already installed "
        "and run %(SERVER_SOFTWARE_NAME)s on this system."
    )
    % {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
    replace_existing_question=_(
        "Are you sure you want to replace the session secret key?"
    ),
)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the session secret key.

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
        logger.debug(_("The session secret key was successfully updated."))
        return True

    logger.error(_("The session secret key was not updated."))
    return False
