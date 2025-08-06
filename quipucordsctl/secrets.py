"""Secrets module handles secrets-related inputs and checks."""

import difflib
import getpass
import logging
import secrets
from dataclasses import dataclass
from gettext import gettext as _

logger = logging.getLogger(__name__)


class DisableLogger:
    """Context manager that disables logging messages."""

    def __enter__(self):
        """Disable logging messages."""
        logging.disable(logging.CRITICAL)

    def __exit__(self, exc_type, exc_value, traceback):
        """Resume logging messages."""
        logging.disable(logging.NOTSET)


def prompt_secret(secret_name: str, **kwargs) -> str | None:
    """Prompt the user to enter a new secret value."""
    new_secret = getpass.getpass(
        _("Enter new %(secret_name)s: ") % {"secret_name": secret_name},
    )
    confirm_secret = getpass.getpass(
        _("Confirm new %(secret_name)s: ") % {"secret_name": secret_name},
    )
    if new_secret != confirm_secret:
        logger.error(
            _("Your %(secret_name)s inputs do not match."), {"secret_name": secret_name}
        )
        return None
    return new_secret if check_secret(new_secret, secret_name, **kwargs) else None


def generate_random_secret(length: int) -> str:
    """Generate a random secret value."""
    while True:
        new_secret = secrets.token_urlsafe(length)
        with DisableLogger():
            # It's unlikely but possible for token_urlsafe to generate
            # a value that does not pass our check_secret requirements.
            # Loop and try again just to be safe.
            if check_secret(new_secret):
                return new_secret


@dataclass
class SimilarValueCheck:
    """Class for defining an optional value to check for secret similarity."""

    value: str
    name: str
    max_similarity: float = 1.0


def check_secret(  # noqa: PLR0913
    new_secret: str,
    secret_name: str = _("secret"),  # noqa: S107
    *,
    min_length: int = 16,
    digits: bool = True,
    letters: bool = True,
    not_isdigit: bool = True,
    blocklist: list[str] | None = None,
    check_similar: SimilarValueCheck | None = None,
) -> bool:
    """Check if the new secret value meets required criteria."""
    success = True
    if min_length and len(new_secret) < min_length:
        # mimic MinimumLengthValidator on the server
        logger.error(
            _("Your %(secret_name)s must be at least %(min_length)s characters long."),
            {"secret_name": secret_name, "min_length": min_length},
        )
        success = False
    if digits and not any(c.isdigit() for c in new_secret):
        logger.error(
            _("Your %(secret_name)s must contain a number."),
            {"secret_name": secret_name},
        )
        success = False
    if letters and not any(c.isalpha() for c in new_secret):
        logger.error(
            _("Your %(secret_name)s must contain a letter."),
            {"secret_name": secret_name},
        )
        success = False
    if not_isdigit and new_secret.isdigit():
        # mimic NumericPasswordValidator on the server
        logger.error(
            _("Your %(secret_name)s cannot be entirely numeric."),
            {"secret_name": secret_name},
        )
        success = False
    if blocklist and new_secret in blocklist:
        # mimic CommonPasswordValidator on the server
        logger.error(
            _("Your %(secret_name)s cannot be used because it is blocked."),
            {"secret_name": secret_name},
        )
        success = False
    if check_similar and (
        difflib.SequenceMatcher(a=new_secret, b=check_similar.value).quick_ratio()
        >= check_similar.max_similarity
    ):
        # mimic UserAttributeSimilarityValidator on the server
        logger.error(
            _("Your %(secret_name)s is too similar to your %(similar_name)s."),
            {"secret_name": secret_name, "similar_name": check_similar.name},
        )
        success = False

    return success
