"""Reset the server's login password."""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import secrets, shell_utils

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

    with shell_utils.get_podman_client() as podman_client:
        if podman_client.secrets.exists(PODMAN_SECRET_NAME):
            logger.debug(
                _("A podman secret %(PODMAN_SECRET_NAME)s already exists."),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
            podman_client.secrets.remove(PODMAN_SECRET_NAME)
            logger.info(
                _("Old podman secret %(PODMAN_SECRET_NAME)s was removed."),
                {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
            )
        podman_client.secrets.create(PODMAN_SECRET_NAME, new_password)
        logger.info(
            _("New podman secret %(PODMAN_SECRET_NAME)s was set."),
            {"PODMAN_SECRET_NAME": PODMAN_SECRET_NAME},
        )
    return True
