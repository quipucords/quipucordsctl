"""Helper functions to support argparse."""

import argparse
import enum
import logging
import types
from gettext import gettext as _

from quipucordsctl import settings

logger = logging.getLogger(__name__)


class DisplayGroups(enum.Enum):
    """Enum of possible display group names for argparse help text."""

    MAIN = _("Main Commands")
    CONFIG = _("Advanced Configuration Commands")
    DIAGNOSTICS = _("Diagnostic Commands")
    OTHER = _("Other Commands")


def add_command(  # noqa: PLR0913
    subparser: argparse._SubParsersAction,
    command_module: types.ModuleType,
    argparse_display_group: argparse._ArgumentGroup,
    command_name: str,
    help_text: str | None,
    description: str | None,
    epilog: str | None,
) -> None:
    """
    Add a command to the parser and make it display under a specific group name.

    This function enables us to change the display of commands to list under
    different groupings in the help text while not actually affecting the functional
    behavior of the parser and its arguments.

    We use this helper function to encapsulate making direct changes to subparser
    internals that are not exposed through normal Python APIs. We access some member
    properties that are `_` "protected" which *could* be problematic in theory, but
    in practice these properties and how they are used are very stable and have not
    changed in any significant way for a long time.
    """
    usage = _("{prog} [OPTIONS...] {name} [COMMAND OPTIONS...]").format(
        prog=settings.PROGRAM_NAME, name=command_name
    )
    command_parser = subparser.add_parser(
        command_name,
        help=help_text,
        description=description,
        epilog=epilog,
        usage=usage,
    )
    if hasattr(command_module, "setup_parser"):
        command_module.setup_parser(command_parser)

    # Here we move the actual action object (the last one added) to our display group.
    # The above call to subparser.add_parser *should always* append to _choices_actions.
    # If future Python internals have changed unexpectedly, this will fail loudly and
    # raise an exception to the top of the stack, ending execution.
    try:
        if subparser._choices_actions[-1].dest == command_name:
            argparse_display_group._group_actions.append(subparser._choices_actions[-1])
        else:
            raise ValueError(
                _(
                    "subparser._choices_actions[-1].dest was %(value)s, "
                    "but add_command expected %(command_name)s"
                )
                % {
                    "value": repr(subparser._choices_actions[-1].dest),
                    "command_name": repr(command_name),
                }
            )
    except (AttributeError, IndexError, KeyError, ValueError) as e:
        logger.exception(
            _(
                "Failed to add command '%(command_name)s' to argparse display group "
                "due to an unexpected error: %(error)s"
            ),
            {"command_name": command_name, "error": str(e)},
        )
        raise


def non_negative_integer(value: str) -> int:
    """Enforce non-negative integer value."""
    error_msg = _("invalid non-negative integer value: '%(value)s'") % {"value": value}
    try:
        int_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(error_msg) from error
    if int_value < 0:
        raise argparse.ArgumentTypeError(error_msg)
    return int_value
