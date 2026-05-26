"""Start the server."""

import argparse
import textwrap
from gettext import gettext as _

from quipucordsctl import argparse_utils, podman_utils, settings, systemctl_utils

_START_SUCCESS_MESSAGE = _("%(server_software_name)s server started successfully.")


def get_display_group() -> argparse_utils.DisplayGroups:
    """Get the group identifier for displaying this command in CLI help text."""
    return argparse_utils.DisplayGroups.MAIN


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Start the %(server_software_name)s server") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Start the %(server_software_name)s server.
            Before starting, this command checks for and pulls any missing container
            images. It then starts the server and waits for it to become active.
            If the server fails to start, a non-zero exit code is returned along with
            diagnostic information and guidance on how to investigate the failure.
            """
        )
    ) % {"server_software_name": settings.SERVER_SOFTWARE_NAME}


def run(args: argparse.Namespace) -> bool:
    """Start the server, ensuring requirements are met and images are present."""
    systemctl_utils.ensure_systemd_user_session()
    podman_utils.ensure_podman_socket()
    podman_utils.ensure_cgroups_v2()

    if not podman_utils.ensure_images():
        return False

    if not systemctl_utils.start_service():
        return False

    if not args.quiet:
        print(
            _START_SUCCESS_MESSAGE
            % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
        )
    return True
