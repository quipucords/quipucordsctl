"""Secrets module handles secrets-related inputs and checks."""

import dataclasses
import difflib
import getpass
import logging
import secrets
from gettext import gettext as _

from quipucordsctl import podman_utils, settings, shell_utils

logger = logging.getLogger(__name__)

DEFAULT_MIN_LENGTH = 16


class DisableLogger:
    """Context manager that disables logging messages."""

    def __enter__(self):
        """Disable logging messages."""
        logging.disable(logging.CRITICAL)

    def __exit__(self, exc_type, exc_value, traceback):
        """Resume logging messages."""
        logging.disable(logging.NOTSET)


@dataclasses.dataclass
class ResetSecretMessages:
    """User-facing strings that may be different for each secret being reset."""

    manual_reset_warning: str = _(
        "You should only manually reset this secret if you "
        "understand how it is used, and you are addressing a specific issue. "
        "We strongly recommend using the automatically generated value for "
        "this secret instead of manually entering one."
    )
    manual_reset_question: str = _(
        "Are you sure you want to manually reset this secret?"
    )
    replace_existing_warning: str = (
        _(
            "This secret already exists with a value. "
            "Resetting this secret to a new value "
            "may result in data loss if you have already installed "
            "and run %(SERVER_SOFTWARE_NAME)s on this system."
        )
        % {"SERVER_SOFTWARE_NAME": settings.SERVER_SOFTWARE_NAME},
    )
    replace_existing_question: str = _(
        "Are you sure you want to replace the existing secret?"
    )
    prompt_enter_value: str = _("Enter new secret value: ")
    prompt_confirm_value: str = _("Confirm new secret value: ")
    prompt_values_no_match: str = _("Your inputs do not match.")
    was_not_updated: str = _("This secret was not updated.")

    check_failed_min_length: str = _(
        "The value for this secret must be at least %(min_length)s characters long."
    )
    check_failed_requires_a_number: str = _(
        "The value for this secret must contain a number."
    )
    check_failed_requires_a_letter: str = _(
        "The value for this secret must contain a letter."
    )
    check_failed_cannot_be_entirely_numeric: str = _(
        "The value for this secret cannot by entirely numeric."
    )
    check_failed_blocked: str = _(
        "The value you provided cannot be used because it is blocked."
    )
    check_failed_too_similar: str = _(
        "The value you provided is too similar to another secret's value."
    )
    result_updated: str = _("The secret was successfully updated.")
    result_not_updated: str = _("The secret was not updated.")


# Defaults are generic enough if no customization is desired.
_default_reset_secret_messages = ResetSecretMessages()


def prompt_secret(messages: ResetSecretMessages | None = None) -> str | None:
    """Prompt the user to enter a new secret value."""
    if settings.runtime.quiet:
        return None

    if not messages:
        messages = _default_reset_secret_messages

    new_secret = getpass.getpass(messages.prompt_enter_value)
    confirm_secret = getpass.getpass(messages.prompt_confirm_value)
    if new_secret != confirm_secret:
        logger.error(messages.prompt_values_no_match)
        return None
    return new_secret


def generate_random_secret(**check_args) -> str:
    """Generate a random secret value."""
    length = check_args.get("min_length", DEFAULT_MIN_LENGTH)
    while True:
        new_secret = secrets.token_urlsafe(length)
        with DisableLogger():
            # It's unlikely but possible for token_urlsafe to generate
            # a value that does not pass our check_secret requirements.
            # Loop and try again just to be safe.
            if check_secret(new_secret, **check_args):
                return new_secret


def confirm_replace_existing(
    messages: ResetSecretMessages | None = None,
) -> bool:
    """Confirm that the user wants to replace an existing secret."""
    if not messages:
        messages = _default_reset_secret_messages

    logger.warning(messages.replace_existing_warning)
    return shell_utils.confirm(messages.replace_existing_question)


def confirm_allow_nonrandom(messages: ResetSecretMessages | None = None) -> bool:
    """Confirm that the user wants to set a non-random value from their input."""
    if not messages:
        messages = _default_reset_secret_messages

    logger.warning(messages.manual_reset_warning)
    return shell_utils.confirm(messages.manual_reset_question)


def reset_secret(
    podman_secret_name: str,
    messages: ResetSecretMessages | None = None,
    must_confirm_replace_existing: bool = False,
    **kwargs,  # additional kwargs will pass to get_new_secret_value
):
    """
    Reset the given podman secret, reading an env var or prompting the user if needed.

    This function can be considered a main function or entrypoint for resetting any
    secret-like values. It warns if a value was already set, optionally reads from
    an environment variable, validates user input, and generates a new pseudorandom
    value if no input was given.

    Returns True if everything succeeded, else False because some input validation
    failed or the user declined a confirmation prompt. The functions called by this
    function log appropriate messages to explain any potential failures whenever
    they may occur.
    """
    if not messages:
        messages = _default_reset_secret_messages

    already_exists = podman_utils.secret_exists(podman_secret_name)
    new_secret = get_new_secret_value(
        podman_secret_name=podman_secret_name,
        messages=messages,
        must_confirm_replace_existing=must_confirm_replace_existing and already_exists,
        **kwargs,
    )

    if new_secret and podman_utils.set_secret(
        podman_secret_name, new_secret, already_exists
    ):
        logger.debug(messages.result_updated)
        return True

    logger.error(messages.result_not_updated)
    return False


def get_new_secret_value(  # noqa: PLR0911, PLR0913, C901
    podman_secret_name: str,
    messages: ResetSecretMessages | None = None,
    *,
    env_var_name: str | None = None,
    check_requirements: dict | None = None,
    must_confirm_replace_existing: bool = False,
    must_confirm_allow_nonrandom: bool = True,
    must_prompt_interactive_input: bool = False,
    may_prompt_interactive_input: bool = False,
) -> str | None:
    """
    Return a new secret value following a possibly complex interaction of inputs.

    Several of this function's conditions could be merged or use more walrus operators
    to reduce the number of variable assignments, but the myriad use cases and types of
    input handling are already complex enough, and the author of this code favored using
    many early returns (see: PLR0911) with individual inline comment explanations to
    provide more readable (and hopefully maintainable) code to fellow human developers.

    Returns the new secret value if everything succeeded, else None.
    """
    if must_confirm_replace_existing and not confirm_replace_existing(messages):
        # Secret value already exists, and user decided not to replace it.
        return None

    new_secret = None

    if not must_prompt_interactive_input and env_var_name:
        # Some commands have an optional "--prompt" argument that the user can set,
        # which manifests here as 'must_prompt_interactive_input', and we will honor
        # their request for a prompt and skip env var handling if requested.

        if new_secret := shell_utils.get_env(env_var_name):
            if not check_secret(new_secret, messages, **check_requirements):
                # env var was found, but it failed required checks
                return None
            if must_confirm_allow_nonrandom and not confirm_allow_nonrandom(messages):
                # env var passed checks, but user declined setting a nonrandom value
                return None

    if (
        must_prompt_interactive_input or may_prompt_interactive_input
    ) and not new_secret:
        # Some commands like reset_admin_password want to offer an interactive prompt
        # but *do not require* the user to see the prompt if the correct env var exists,
        # and that use case as 'may_prompt_interactive_input'. If we found a valid value
        # from the env var, we just use that value and skip this whole section.

        if must_confirm_allow_nonrandom and not confirm_allow_nonrandom(messages):
            # user declined setting a nonrandom value
            return None
        if not (new_secret := prompt_secret(messages)):
            # input was requested, but quiet mode prevented user input
            return None
        if not check_secret(new_secret, messages, **check_requirements):
            # user input failed required checks
            return None

    if new_secret:
        return new_secret

    # no interactive input? no env var? default to generating a random value.
    new_secret = generate_random_secret(**check_requirements)
    logger.info(
        _(
            "New value for podman secret '%(PODMAN_SECRET_NAME)s' "
            "was randomly generated."
        ),
        {"PODMAN_SECRET_NAME": podman_secret_name},
    )

    return new_secret


@dataclasses.dataclass
class SimilarValueCheck:
    """Class for defining an optional value to check for secret similarity."""

    value: str
    name: str
    max_similarity: float = 1.0


def check_secret(  # noqa: PLR0913
    new_secret: str,
    messages: ResetSecretMessages | None = None,
    *,
    min_length: int = DEFAULT_MIN_LENGTH,
    digits: bool = True,
    letters: bool = True,
    not_isdigit: bool = True,
    blocklist: list[str] | None = None,
    check_similar: SimilarValueCheck | None = None,
) -> bool:
    """Check if the new secret value meets required criteria."""
    if not messages:
        messages = _default_reset_secret_messages

    success = True
    if min_length and len(new_secret) < min_length:
        # mimic MinimumLengthValidator on the server
        logger.error(messages.check_failed_min_length, {"min_length": min_length})
        success = False
    if digits and not any(c.isdigit() for c in new_secret):
        logger.error(messages.check_failed_requires_a_number)
        success = False
    if letters and not any(c.isalpha() for c in new_secret):
        logger.error(messages.check_failed_requires_a_letter)
        success = False
    if not_isdigit and new_secret.isdigit():
        # mimic NumericPasswordValidator on the server
        logger.error(messages.check_failed_cannot_be_entirely_numeric)
        success = False
    if blocklist and new_secret in blocklist:
        # mimic CommonPasswordValidator on the server
        logger.error(messages.check_failed_blocked)
        success = False
    if check_similar and (
        difflib.SequenceMatcher(a=new_secret, b=check_similar.value).quick_ratio()
        >= check_similar.max_similarity
    ):
        # mimic UserAttributeSimilarityValidator on the server
        logger.error(messages.check_failed_too_similar)
        success = False

    return success
