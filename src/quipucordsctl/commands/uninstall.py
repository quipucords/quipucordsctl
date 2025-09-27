"""Uninstall the server."""

import argparse
import configparser
import logging
import shutil
from gettext import gettext as _
from pathlib import Path

from quipucordsctl import constants, podman_utils, settings, shell_utils
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
    shell_utils.run_command(constants.SYSTEMCTL_USER_STOP_QUIPUCORDS_APP)
    shell_utils.run_command(constants.SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK)
    return True


def remove_container_images() -> bool:
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

            for section in unit_file_config.sections():
                if section == "Container":
                    if image := unit_file_config.get(section, "Image"):
                        unique_images.add(image)

    if not unique_images:
        return True

    all_removed = all(podman_utils.remove_image(image) for image in unique_images)
    if not all_removed:
        logger.warning(
            _("At least one image failed to be removed"),
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
        if env_file_path.exists():
            logger.info(
                _("Removing the %(server_software_name)s env file %(env_file_path)s."),
                {
                    "server_software_name": settings.SERVER_SOFTWARE_NAME,
                    "env_file_path": env_file_path,
                },
            )
            env_file_path.unlink()

    for unit_file in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        unit_file_path = Path(settings.SYSTEMD_UNITS_DIR) / unit_file
        if unit_file_path.exists():
            logger.info(
                _(
                    "Removing the %(server_software_name)s"
                    " unit file %(unit_file_path)s."
                ),
                {
                    "server_software_name": settings.SERVER_SOFTWARE_NAME,
                    "unit_file_path": unit_file_path,
                },
            )
            unit_file_path.unlink()

    if (
        settings.SYSTEMD_GENERATED_SERVICES_DIR
        and settings.SYSTEMD_GENERATED_SERVICES_DIR.exists()
    ):
        for service_file in settings.SYSTEMD_SERVICE_FILENAMES:
            service_file_path = settings.SYSTEMD_GENERATED_SERVICES_DIR / service_file
            if service_file_path.exists():
                logger.info(
                    _(
                        "Removing the %(server_software_name)s"
                        " service file %(service_file_path)s."
                    ),
                    {
                        "server_software_name": settings.SERVER_SOFTWARE_NAME,
                        "service_file_path": service_file_path,
                    },
                )
                service_file_path.unlink()
    return True


def reload_daemon() -> bool:
    """Reset systemctl failures and reload the daemon."""
    logger.info(_("Reloading the systemctl daemon ..."))
    shell_utils.run_command(constants.SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(constants.SYSTEMCTL_USER_DAEMON_RELOAD_CMD)
    return True


def remove_data() -> bool:
    """Remove the quipucords data."""
    logger.info(
        _("Removing the %(server_software_name)s data ..."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    for data_dir in settings.SERVER_DATA_SUBDIRS_EXCLUDING_DB.values():
        shutil.rmtree(data_dir, ignore_errors=True)
    return True


def remove_secrets() -> bool:
    """Remove the quipucords podman secrets."""
    logger.info(
        _("Removing the %(server_software_name)s secrets ..."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    for key in constants.QUIPUCORDS_SECRET_KEYS:
        if not podman_utils.delete_secret(key):
            return False
    return True


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Uninstall the server."""
    if not stop_containers():
        return False
    if not remove_container_images():
        return False
    if not remove_services():
        return False
    if not reload_daemon():
        return False
    if not remove_data():
        return False
    if not remove_secrets():
        return False
    print(
        _("%(server_software_name)s uninstalled successfully.")
        % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
    )
    return True
