"""
Reset the Redis password.

The Redis password is only used for communicating with the local Redis server.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings

logger = logging.getLogger(__name__)
PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["redis"]
ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}REDIS_PASSWORD"
MIN_LENGTH = 64
REQUIREMENTS = {"min_length": MIN_LENGTH}


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the Redis password")


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Reset the %(server_software_name)s Redis password.
            The %(server_software_name)s server internally uses this password
            to communicate with its local Redis server.
            The `%(command_name)s` command uses the value of the `%(env_var_name)s`
            environment variable or generates a cryptographically strong random value.
            Use `--prompt` only if you need to manually enter a value.
            Resetting the Redis password after running the
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
            "Prompt for custom Redis password "
            "(default: no prompt, generate a random value)"
        ),
    )


def is_set() -> bool:
    """Check if the Redis password is already set."""
    return podman_utils.secret_exists(PODMAN_SECRET_NAME)


reset_secret_messages = secrets.ResetSecretMessages(
    manual_reset_warning=_(
        "%(program_name)s generates cryptographically strong random passwords by "
        "default. You should manually reset the Redis password only if "
        "your environment specifically requires a custom value."
    ),
    manual_reset_question=_(
        "Are you sure you want to manually set a custom Redis password?"
    ),
    result_updated=_("The Redis password was successfully updated."),
    result_not_updated=_("The Redis password was not updated."),
)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the Redis password.

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
