"""Uninstall the server."""

import argparse
import logging
from gettext import gettext as _

from .. import settings

logger = logging.getLogger(__name__)
NOT_A_COMMAND = True  # Until we complete the implementation.

def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Uninstall the %(server_software_name)s server.") % {
        "server_software_name": settings.SERVER_SOFTWARE
    }

def run(args: argparse.Namespace) -> None:
    """Uninstall the server."""
    logger.warning(_("%(command)s is not yet implemented."), {"command": __name__})
    # TODO Implement this.
