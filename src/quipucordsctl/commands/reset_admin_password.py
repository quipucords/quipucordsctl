"""Reset the login password."""
# TODO Should this command also conditionally restart the server?

import argparse
import logging
from gettext import gettext as _

from quipucordsctl import podman_utils, secrets, settings

logger = logging.getLogger(__name__)
ADMIN_PASSWORD_PODMAN_SECRET_NAME = settings.QUIPUCORDS_SECRETS["server"]  # noqa: S105
ADMIN_PASSWORD_ENV_VAR_NAME = f"{settings.ENV_VAR_PREFIX}SERVER_PASSWORD"
PASSWORD_MIN_LENGTH = 10
PASSWORD_BLOCKLIST = ["dscpassw0rd", "qpcpassw0rd"]
DEFAULT_USERNAME = "admin"
PASSWORD_USERNAME_MAX_SIMILARITY = 0.7


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Reset the admin login password.")


def is_set() -> bool:
    """Check if the admin password is already set."""
    return podman_utils.secret_exists(ADMIN_PASSWORD_PODMAN_SECRET_NAME)


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Reset the admin login password."""
    check_kwargs = {
        "min_length": PASSWORD_MIN_LENGTH,
        "blocklist": PASSWORD_BLOCKLIST,
        "check_similar": secrets.SimilarValueCheck(
            value=DEFAULT_USERNAME,
            name=_("admin login username"),
            max_similarity=PASSWORD_USERNAME_MAX_SIMILARITY,
        ),
    }
    new_password, invalid = secrets.read_from_env(
        ADMIN_PASSWORD_ENV_VAR_NAME, _("admin login password"), **check_kwargs
    )
    if invalid:
        # Early return because env var was found but failed checks.
        return False
    elif not new_password and not (
        new_password := secrets.prompt_secret(_("admin login password"), **check_kwargs)
    ):
        return False
    if not podman_utils.set_secret(ADMIN_PASSWORD_PODMAN_SECRET_NAME, new_password):
        logger.error(_("The admin login password was not updated."))
        return False
    return True
