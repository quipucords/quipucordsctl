"""Uninstall the server."""

import argparse
import configparser
import logging
import shutil
from gettext import gettext as _
from pathlib import Path

from quipucordsctl import podman_utils, settings, shell_utils
from quipucordsctl.systemdunitparser import SystemdUnitParser

logger = logging.getLogger(__name__)


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Uninstall the %(server_software_name)s server.") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def stop_containers() -> bool:
    """Stop all containers."""
    logger.info(
        _("Stopping the %(server_software_name)s server."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    __, __, exit_code = shell_utils.run_command(
        settings.SYSTEMCTL_USER_LIST_QUIPUCORDS_APP, raise_error=False
    )
    if exit_code == 0:
        try:
            shell_utils.run_command(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_APP)
            shell_utils.run_command(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK)
        except Exception as error:  # noqa: BLE001
            logger.error(
                _("Could not stop the %(server_software_name)s server."),
                {"server_software_name": settings.SERVER_SOFTWARE_NAME},
            )
            logger.debug(
                _("Error stopping %(server_software_name)s - %(error)s"),
                {
                    "server_software_name": settings.SERVER_SOFTWARE_NAME,
                    "error": error,
                },
            )
            return False
    return True


def remove_container_images():
    """Remove container images."""
    logger.info(
        _("Removing the %(server_software_name)s container images."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    unique_images = set()

    for unit_file in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        unit_file_path = Path(settings.SYSTEMD_UNITS_DIR) / unit_file
        if unit_file_path.suffix == ".container" and unit_file_path.exists():
            unit_file_config = SystemdUnitParser()
            try:
                unit_file_config.read(unit_file_path)
            except configparser.MissingSectionHeaderError:
                logger.warning(
                    _(
                        "Skipping the %(unit_file)s container file due to"
                        " missing section headers."
                    ),
                    {"unit_file": unit_file},
                )

            if image := unit_file_config.get("Container", "Image"):
                unique_images.add(image)

    if unique_images:
        all_removed = all(podman_utils.remove_image(image) for image in unique_images)
        if not all_removed:
            logger.warning(
                _("At least one image failed to be removed"),
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
    logger.info(_("Reloading the systemctl daemon ..."))
    shell_utils.run_command(settings.SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD)
    return True


def remove_data():
    """Remove the quipucords data."""
    logger.info(
        _("Removing the %(server_software_name)s data ..."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    for data_dir in settings.SERVER_DATA_SUBDIRS_EXCLUDING_DB.values():
        shutil.rmtree(data_dir, ignore_errors=True)


def remove_secrets() -> bool:
    """Remove the quipucords podman secrets."""
    logger.info(
        _("Removing the %(server_software_name)s secrets ..."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    for key in settings.QUIPUCORDS_SECRET_KEYS:
        if not podman_utils.delete_secret(key):
            return False
    return True


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Uninstall the server."""
    if not stop_containers():
        return False
    remove_container_images()
    if not remove_services():
        return False
    if not reload_daemon():
        return False
    remove_data()
    if not remove_secrets():
        return False
    print(
        _("%(server_software_name)s uninstalled successfully.")
        % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
    )
    return True
