"""Upgrade the quipucords-app service, or install it if absent."""

import argparse
import logging
import textwrap
from gettext import gettext as _

from quipucordsctl import argparse_utils, podman_utils, settings, systemctl_utils
from quipucordsctl.commands import install

logger = logging.getLogger(__name__)


def get_display_group() -> argparse_utils.DisplayGroups:
    """Get the group identifier for displaying this command in CLI help text."""
    return argparse_utils.DisplayGroups.MAIN


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Upgrade the %(server_software_name)s server") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Upgrade the %(server_software_name)s software if it is already installed,
            or install the software if it is not present.
            The `%(command_name)s` command will stop any currently running
            %(server_software_name)s services before attempting to upgrade them.
            The `%(command_name)s` command may attempt to pull new images from
            the remote container registry, and that operation may require you to
            run a `podman login` command separately to refresh your registry
            credentials.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
    }


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-P",
        "--no-pull",
        action="store_true",
        help=_(
            "Do not automatically pull the latest podman images "
            "(default: pull, requires network connection)"
        ),
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=argparse_utils.non_negative_integer,
        default=settings.DEFAULT_PODMAN_PULL_TIMEOUT,
        help=_(
            "Maximum number of seconds to wait for `podman pull` to complete "
            "(default: %(default)s)"
        )
        % {"default": settings.DEFAULT_PODMAN_PULL_TIMEOUT},
    )


def pull_latest_images(timeout: int | None = None) -> bool:
    """
    Pull the images defined in the updated configs.

    If any pull command fails, perhaps due to network connectivity or missing auth,
    then log appropriate error messages and return False. Else, return True if all
    images pull successfully.
    """
    successes = [
        podman_utils.pull_image(image)
        for image in podman_utils.list_expected_podman_container_images()
    ]
    if not all(successes):
        logger.error(
            _(
                "Failed to pull at least one image. "
                "Please review the logs, check network connectivity, and "
                "verify your podman credentials before trying again."
            )
        )
        return False
    return True


def print_success():
    """Print a success message."""
    print(
        _(
            textwrap.dedent(
                """
                Upgrade completed successfully.
                Please run the following command to restart the
                %(server_software_name)s server:

                    systemctl --user restart %(server_software_package)s-app
                """  # noqa: E501
            )
        )
        % {
            "server_software_name": settings.SERVER_SOFTWARE_NAME,
            "server_software_package": settings.SERVER_SOFTWARE_PACKAGE,
        },
    )


def run(args: argparse.Namespace) -> bool:
    """Stop the quipucords-app service."""
    if not systemctl_utils.stop_service():
        logger.error(
            _(
                "Could not upgrade the %(server_software_name)s software because "
                "the service failed to stop normally."
            ),
            {"server_software_name": settings.SERVER_SOFTWARE_NAME},
        )
        return False

    install_args = argparse.Namespace(
        # Force "quiet" to silence the nested "install" command's success message.
        **{**vars(args), "quiet": True}
    )
    if not install.run(install_args):
        logger.error(
            _(
                "Could not upgrade the %(server_software_name)s software because "
                "the software failed to install normally."
            ),
            {"server_software_name": settings.SERVER_SOFTWARE_NAME},
        )
        return False

    if args.no_pull:
        logger.warning(
            _(
                "You requested an upgrade without pulling the latest podman images. "
                "Please verify that you have the latest podman images before you "
                "restart the %(server_software_name)s software, or the software may "
                "not run correctly."
            ),
            {"server_software_name": settings.SERVER_SOFTWARE_NAME},
        )
    elif not pull_latest_images(args.timeout):
        return False

    if not args.quiet:
        print_success()
    return True
