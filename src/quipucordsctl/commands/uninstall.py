"""Uninstall the server."""

import argparse
import logging
import shutil
import textwrap
from gettext import gettext as _
from pathlib import Path

from quipucordsctl import (
    argparse_utils,
    loginctl_utils,
    podman_utils,
    settings,
    shell_utils,
    systemctl_utils,
)

logger = logging.getLogger(__name__)


def get_display_group() -> argparse_utils.DisplayGroups:
    """Get the group identifier for displaying this command in CLI help text."""
    return argparse_utils.DisplayGroups.MAIN


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Uninstall the %(server_software_name)s server") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Completely uninstall the %(server_software_name)s software.
            The `%(command_name)s` command will stop any currently running
            %(server_software_name)s services and remove their container images,
            secrets, configuration files, logs, and other
            %(server_software_name)s-specific data files from your home directory.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
    }


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "--keep-data-dirs",
        action="store_true",
        help=_("Do not remove instance data in %(pathname)s (default: remove it)")
        % {"pathname": settings.SERVER_DATA_DIR},
    )


def remove_container_images() -> bool:
    """Remove container images."""
    logger.info(
        _("Removing the %(server_software_name)s container images."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )

    successes = [
        podman_utils.remove_image(image)
        for image in podman_utils.list_expected_podman_container_images()
    ]
    if not all(successes):
        logger.warning(
            _(
                "Podman failed to remove at least one image. Please check logs "
                "and manually remove any remaining images if necessary."
            ),
        )
        return False
    return True


def remove_file(file_path: Path) -> bool:
    """Remove a file."""
    logger.info(
        _("Removing the %(server_software_name)s file %(file_path)s."),
        {
            "server_software_name": settings.SERVER_SOFTWARE_NAME,
            "file_path": file_path,
        },
    )
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as error:  # noqa: BLE001
            # While we can catch specific, PermissionError and others
            # os.unlink can also return other errors, let's catch them all here.
            logger.error(
                _(
                    "The uninstall command failed to remove"
                    " the file %(file_path)s - %(error)s."
                ),
                {"file_path": file_path, "error": error},
            )
            return False
    else:
        logger.debug(
            _(
                "The uninstall command did not find"
                " the file %(file_path)s which it expected to remove."
            ),
            {"file_path": file_path},
        )
    return True


def remove_services() -> bool:
    """Remove services."""
    logger.info(
        _("Removing the %(server_software_name)s services."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )

    for env_file in settings.TEMPLATE_SERVER_ENV_FILENAMES:
        env_file_path = Path(settings.SERVER_ENV_DIR) / env_file
        if not remove_file(env_file_path):
            return False

    for unit_file in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        unit_file_path = Path(settings.SYSTEMD_UNITS_DIR) / unit_file
        if not remove_file(unit_file_path):
            return False

    if (
        settings.SYSTEMD_GENERATED_SERVICES_DIR
        and settings.SYSTEMD_GENERATED_SERVICES_DIR.exists()
    ):
        for service_file in settings.SYSTEMD_SERVICE_FILENAMES:
            service_file_path = settings.SYSTEMD_GENERATED_SERVICES_DIR / service_file
            if not remove_file(service_file_path):
                return False
    return True


def reload_daemon() -> bool:
    """Reset systemctl failures and reload the daemon."""
    logger.info(_("Reloading the systemctl daemon."))
    shell_utils.run_command(settings.SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD)
    return True


def remove_data(keep_data_dirs=False) -> bool:
    """
    Remove the quipucords data, or tell the user it was not removed.

    Note: This function returns a bool simply to provide a consistent interface with the
    other uninstall-related functions. Although this always returns True today, perhaps
    later we will find a reason for this to return False.
    """
    if keep_data_dirs:
        logger.info(
            _(
                "Not removing the %(server_software_name)s data "
                "because --keep-data-dirs flag was passed."
            ),
            {"server_software_name": settings.SERVER_SOFTWARE_NAME},
        )
        return True

    logger.info(
        _("Removing the %(server_software_name)s data."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    for data_dir in settings.SERVER_DATA_SUBDIRS_EXCLUDING_DB.values():
        shutil.rmtree(data_dir, ignore_errors=True)
    return True


def remove_secrets() -> bool:
    """Remove the quipucords podman secrets."""
    logger.info(
        _("Removing the %(server_software_name)s secrets."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    successes = [
        podman_utils.delete_secret(key)
        for key in settings.QUIPUCORDS_SECRET_KEYS
        if podman_utils.secret_exists(key)
    ]
    if not all(successes):
        logger.error(
            _(
                "Podman failed to remove at least one secret. Please check logs "
                "and manually remove any remaining secrets if necessary."
            )
        )
        return False
    return True


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Uninstall the server."""
    # Important implementation detail:
    # We nest this list of function call results inside `all` because we want all the
    # functions to execute, but we only consider the collective operation to be
    # successful if all completed successfully. Even if one fails, the others should
    # still try to run so that we uninstall as much as possible. For this reason, we
    # cannot simply chain calls together using "and" because we do not want one False to
    # prevent later functions from running.
    success = all(
        [
            systemctl_utils.stop_service(),
            remove_container_images(),
            remove_services(),
            systemctl_utils.reload_daemon(),
            remove_data(args.keep_data_dirs),
            remove_secrets(),
            loginctl_utils.check_linger(),
        ]
    )

    if not args.quiet:
        if success:
            print(
                _("%(server_software_name)s uninstalled successfully.")
                % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
            )
        else:
            print(
                _(
                    "%(program_name)s uninstall encountered an unexpected error. "
                    "Check logs and manually review that %(server_software_name)s "
                    "uninstalled completely."
                )
                % {
                    "program_name": settings.PROGRAM_NAME,
                    "server_software_name": settings.SERVER_SOFTWARE_NAME,
                }
            )
    return success
