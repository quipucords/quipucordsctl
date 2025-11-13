"""Helper functions to support argparse."""

import argparse
from gettext import gettext as _


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
