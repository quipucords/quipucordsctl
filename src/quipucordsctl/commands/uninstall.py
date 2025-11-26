"""Uninstall the server."""

import argparse
import logging
import shutil
from gettext import gettext as _
from pathlib import Path

from quipucordsctl import podman_utils, settings, shell_utils, systemctl_utils
from quipucordsctl.loginctl_utils import check_linger

logger = logging.getLogger(__name__)


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Uninstall the %(server_software_name)s server.") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "--keep-data-dirs",
        action="store_true",
        help=_("Do not remove instance data in %(pathname)s (default: remove it)")
        % {"pathname": settings.SERVER_DATA_DIR},
    )


def remove_container_images():
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


def remove_data(keep_data_dirs=False):
    """Remove the quipucords data, or tell the user it was not removed."""
    if keep_data_dirs:
        logger.info(
            _(
                "Not removing the %(server_software_name)s data "
                "because --keep-data-dirs flag was passed."
            ),
            {"server_software_name": settings.SERVER_SOFTWARE_NAME},
        )
        return

    logger.info(
        _("Removing the %(server_software_name)s data."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    for data_dir in settings.SERVER_DATA_SUBDIRS_EXCLUDING_DB.values():
        shutil.rmtree(data_dir, ignore_errors=True)


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
    if not systemctl_utils.stop_service():
        return False
    remove_container_images()
    if not remove_services():
        return False
    if not systemctl_utils.reload_daemon():
        return False
    remove_data(args.keep_data_dirs)
    if not remove_secrets():
        return False
    if not check_linger():
        return False
    if not args.quiet:
        print(
            _("%(server_software_name)s uninstalled successfully.")
            % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
        )
    return True
