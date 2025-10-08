"""
Reset the admin login password.

The admin login password is how the user auths in the web UI and CLI.
"""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings

logger = logging.getLogger(__name__)

PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["server"]
ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}SERVER_PASSWORD"
MIN_LENGTH = 10
BLOCKLIST = ["dscpassw0rd", "qpcpassw0rd"]
SIMILAR_VALUE = "admin"
MAX_SIMILARITY = 0.7
REQUIREMENTS = {
    "min_length": MIN_LENGTH,
    "blocklist": BLOCKLIST,
    "check_similar": secrets.SimilarValueCheck(
        value=SIMILAR_VALUE,
        name=_("admin login username"),
        max_similarity=MAX_SIMILARITY,
    ),
}


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the admin login password.")


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            The `%(command_name)s` command resets the password you use to log in
            to the %(server_software_name)s software in your web browser and CLI.
            The `%(command_name)s` command will try to use the value from
            the environment variable `%(env_var_name)s` if you have set one.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
        "env_var_name": ENV_VAR_NAME,
    }


def is_set() -> bool:
    """Check if the admin password is already set."""
    return podman_utils.secret_exists(PODMAN_SECRET_NAME)


def run(args: argparse.Namespace) -> bool:
    """
    Reset the admin login password.

    Value prompts random by default, but allow env var.

    Returns True if everything succeeded, else False because some input validation
    failed or the user declined a confirmation prompt.
    """
    already_exists = podman_utils.secret_exists(PODMAN_SECRET_NAME)
    new_secret = secrets.get_new_secret_value(
        podman_secret_name=PODMAN_SECRET_NAME,
        must_confirm_replace_existing=already_exists,
        must_confirm_allow_nonrandom=False,
        must_prompt_interactive_input=False,
        may_prompt_interactive_input=True,
        env_var_name=ENV_VAR_NAME,
        check_requirements=REQUIREMENTS,
    )

    if new_secret and podman_utils.set_secret(
        PODMAN_SECRET_NAME, new_secret, already_exists
    ):
        logger.debug(_("The admin login password was successfully updated."))
        return True

    logger.error(_("The admin login password was not updated."))
    return False
