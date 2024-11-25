"""Uninstall the server."""

import argparse
import logging

from .. import settings

__doc__ = f"Uninstall the {settings.SERVER_SOFTWARE_NAME} server."

logger = logging.getLogger(__name__)
NOT_A_COMMAND = True  # Until we complete the implementation.


def run(args: argparse.Namespace) -> None:
    """Uninstall the server."""
    logger.warning("%s is not yet implemented.", __name__)
    # TODO Implement this.
