"""Reset the server's login password."""

import argparse
import logging
import subprocess
from gettext import gettext as _

from quipucordsctl import secrets

logger = logging.getLogger(__name__)
PODMAN_SECRET_NAME = "quipucords-server-password"  # noqa: S105
PASSWORD_MIN_LENGTH = 10
PASSWORD_BLOCKLIST = ["dscpassw0rd", "qpcpassw0rd"]
DEFAULT_USERNAME = "admin"
PASSWORD_USERNAME_MAX_SIMILARITY = 0.7


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the server's login password.")


def admin_password_is_set() -> bool:
    """Check if the admin password is already set."""
    # TODO `podman secret exists PODMAN_SECRET_NAME`
    # TODO Implement or delete this if we don't actually need it.
    return False


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Reset the server password."""
    check_kwargs = {
        "min_length": PASSWORD_MIN_LENGTH,
        "blocklist": PASSWORD_BLOCKLIST,
        "check_similar": secrets.SimilarValueCheck(
            value=DEFAULT_USERNAME,
            name=_("server login username"),
            max_similarity=PASSWORD_USERNAME_MAX_SIMILARITY,
        ),
    }
    if not (
        new_password := secrets.prompt_secret(
            _("server login password"), **check_kwargs
        )
    ):
        return False

    command = [
        "podman",
        "secret",
        "create",
        "--replace",
        PODMAN_SECRET_NAME,
        "-",
    ]

    try:
        process = subprocess.Popen(  # noqa: S603
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=new_password)

        if process.returncode == 0:
            logger.info(
                _(
                    "podman secret '%(PODMAN_SECRET_NAME)s' "
                    "created/replaced successfully."
                ),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
            logger.debug("podman stdout:")
            logger.debug(stdout)
            return True
        else:
            logger.error(
                _("Failed to create podman secret '%(PODMAN_SECRET_NAME)s'."),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
            # TODO Should we *always* show podman's stderr, or gate it behind -vv?
            logger.debug("podman stderr:")
            logger.debug(stderr)
            return False

    except FileNotFoundError:
        logger.error(
            _(
                "'%(command_name)s' command not found. "
                "Please ensure %(command_name)s is installed and in your PATH."
            ),
            {"command_name": "podman"},
        )
        return False
    except Exception as e:  # noqa: BLE001
        logger.error(_("An unexpected error occurred: %(error)s"), {"error": e})
        return False

    # TODO Should this command also conditionally restart the server?
