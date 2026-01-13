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
PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["session"]
ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}SESSION_SECRET_KEY"
MIN_LENGTH = 64
REQUIREMENTS = {"min_length": MIN_LENGTH}


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the session secret key")


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Reset the %(server_software_name)s session secret key.
            The %(server_software_name)s server internally uses this secret key
            to protect your session and the connection between your web browser
            or CLI and the %(server_software_name)s server.
            The `%(command_name)s` command uses the value of the `%(env_var_name)s`
            environment variable or generates a cryptographically strong random value.
            Use `--prompt` only if you need to manually enter a value.
            Resetting this secret after running the the
            %(server_software_name)s server may break the system or result in data loss.
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
        "%(program_name)s generates cryptographically strong random passwords by "
        "default. You should manually reset the session secret key only if "
        "your environment specifically requires a custom value."
    ),
    manual_reset_question=_(
        "Are you sure you want to manually set a custom session secret key?"
    ),
    replace_existing_warning=_(
        "The session secret key has already been set. "
        "Resetting the session secret key to a new value "
        "may break %(SERVER_SOFTWARE_NAME)s or result in "
        "data loss if you have already installed "
        "and run %(SERVER_SOFTWARE_NAME)s on this system."
    )
    % {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
    replace_existing_question=_(
        "Are you sure you want to replace the session secret key?"
    ),
    result_updated=_("The session secret key was successfully updated."),
    result_not_updated=_("The session secret key was not updated."),
)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the session secret key.

    Read from an env var but give a warning and seek confirmation, or simply
    generate a random value. Support manual interactive input with `--prompt`,
    but also warn and seek confirmation because we prefer a strong random value.
    """
    require_prompt = getattr(args, "prompt", False)
    return secrets.reset_secret(
        podman_secret_name=PODMAN_SECRET_NAME,
        messages=reset_secret_messages,
        must_confirm_replace_existing=False,
        must_confirm_allow_nonrandom=True,
        must_prompt_interactive_input=require_prompt,
        may_prompt_interactive_input=require_prompt,
        env_var_name=ENV_VAR_NAME,
        check_requirements=REQUIREMENTS,
    )
