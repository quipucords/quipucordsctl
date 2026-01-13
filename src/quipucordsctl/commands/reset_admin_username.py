"""
Reset the admin login username.

The admin login username is how the user auths in the web UI and CLI.
"""

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings

logger = logging.getLogger(__name__)

PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["username"]
PASSWORD_SECRET_NAME = settings.QUIPUCORDS_SECRETS["server"]
ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}SERVER_USERNAME"


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the admin login username")


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Reset the username you use to log in to the %(server_software_name)s
            server from your web browser and CLI.
            The `%(command_name)s` command uses the value of the `%(env_var_name)s`
            environment variable or prompts you to manually enter a value.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
        "env_var_name": ENV_VAR_NAME,
    }


def is_set() -> bool:
    """Check if the admin username is already set."""
    return podman_utils.secret_exists(PODMAN_SECRET_NAME)


reset_username_messages = secrets.ResetSecretMessages(
    prompt_enter_value=_("Enter admin login username: "),
    replace_existing_warning=_(
        "The admin login username has already been set. "
        "Resetting the admin login username to a new value "
        "may prevent you from logging in with the old username."
    ),
    replace_existing_question=_(
        "Are you sure you want to replace the existing admin login username?"
    ),
    check_failed_empty=_("Username cannot be empty."),
    check_failed_required_quiet_mode=_(
        "Username is required but cannot be prompted in quiet mode."
    ),
    result_updated=_("The admin login username was successfully updated."),
    result_not_updated=_("The admin login username was not updated."),
)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the admin login username.

    Read from the environment variable or prompt the user for input.
    Require confirmation when replacing an existing username to prevent lockout.
    """
    check_requirements = {
        "min_length": 1,
        "digits": False,
        "letters": False,
        "not_isdigit": False,
    }

    if similar_check := secrets.build_similar_value_check(
        secret_name=PASSWORD_SECRET_NAME,
        display_name=_("admin login password"),
    ):
        check_requirements["check_similar"] = similar_check

    return secrets.reset_username(
        podman_secret_name=PODMAN_SECRET_NAME,
        messages=reset_username_messages,
        must_confirm_replace_existing=True,
        must_prompt_interactive_input=False,
        env_var_name=ENV_VAR_NAME,
        check_requirements=check_requirements,
    )
