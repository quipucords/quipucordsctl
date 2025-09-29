"""Functions to simplify interfacing with podman."""

import logging
import pathlib
import sys
import textwrap
from gettext import gettext as _
from urllib import parse

import podman
import xdg

from quipucordsctl import settings, shell_utils

logger = logging.getLogger(__name__)
MACOS_DEFAULT_PODMAN_URL = "unix:///var/run/docker.sock"

SYSTEMCTL_ENABLE_CMD = ["systemctl", "--user", "enable", "--now", "podman.socket"]
SYSTEMCTL_STATUS_CMD = ["systemctl", "--user", "status", "podman.socket"]
PODMAN_MACHINE_STATE_CMD = ["podman", "machine", "inspect", "--format", "{{.State}}"]

ENABLE_CGROUPS_V2_LONG_MESSAGE = _(
    textwrap.dedent(
        """
        This system is not configured to use cgroups v2 which is required for %(server_software_name)s.
        To enable cgroups v2 (a.k.a. cgroup2fs), you may need to update your kernel arguments and reboot.
        Please run the following commands before using %(server_software_name)s:

            sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"
            sudo reboot
        """  # noqa: E501
    )
)


class PodmanIsNotReadyError(Exception):
    """Exception raised when podman is not ready."""


def ensure_podman_socket(base_url=None):
    """Ensure podman socket is available, as required by the Podman client."""
    logger.debug(_("Ensuring Podman socket is available."))

    if sys.platform == "darwin":
        try:
            stdout, __, __ = shell_utils.run_command(PODMAN_MACHINE_STATE_CMD)
        except Exception:  # noqa: BLE001
            raise PodmanIsNotReadyError(
                _(
                    "Podman command failed unexpectedly. Please install Podman and "
                    "run `podman machine start` before using this command."
                )
            )
        if stdout.strip() != "running":
            raise PodmanIsNotReadyError(
                _(
                    "Podman machine is not running. Please install Podman and "
                    "run `podman machine start` before using this command."
                )
            )
    else:
        try:
            shell_utils.run_command(SYSTEMCTL_ENABLE_CMD)
            shell_utils.run_command(SYSTEMCTL_STATUS_CMD)
        except Exception as e:
            logger.error(
                _(
                    "The 'podman.socket' service failed to start. "
                    "Please check logs and ensure that Podman is correctly installed."
                )
            )
            raise e

    socket_path = pathlib.Path(
        parse.urlparse(
            base_url
            or (
                MACOS_DEFAULT_PODMAN_URL
                if sys.platform == "darwin"
                else str(
                    pathlib.Path(xdg.BaseDirectory.get_runtime_dir(strict=False))
                    / "podman"
                    / "podman.sock"
                )
            )
        ).path
    )
    if not socket_path.exists():
        raise PodmanIsNotReadyError(
            _(
                "Podman socket does not exist at expected path (%(socket_path)s). "
                "Please check logs and ensure that Podman is correctly installed."
                % {"socket_path": socket_path}
            )
        )


def ensure_cgroups_v2():
    """Ensure that cgroups v2 is enabled."""
    with get_podman_client() as podman_client:
        if not podman_client.info().get("host", {}).get("cgroupVersion", None) == "v2":
            print(
                ENABLE_CGROUPS_V2_LONG_MESSAGE
                % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
            )
            raise PodmanIsNotReadyError(_("cgroups v2 is required but not available."))


def get_podman_client(base_url=None) -> podman.PodmanClient:
    """Get a podman client."""
    # podman on macOS/darwin requires a different default base_url,
    # and we should also allow the caller to specify their own.
    ensure_podman_socket(base_url)
    kwargs = (
        {"base_url": base_url}
        if base_url
        else {"base_url": MACOS_DEFAULT_PODMAN_URL}
        if sys.platform == "darwin"
        else {}
    )
    return podman.PodmanClient(**kwargs)


def secret_exists(secret_name: str) -> bool:
    """Simply check if a secret exists."""
    with get_podman_client() as podman_client:
        return podman_client.secrets.exists(secret_name)


def set_secret(secret_name: str, secret_value: str, allow_replace=True) -> bool:
    """Set or replace a podman secret."""
    with get_podman_client() as podman_client:
        if podman_client.secrets.exists(secret_name):
            if allow_replace:
                logger.debug(
                    _("A podman secret %(secret_name)s already exists."),
                    {"secret_name": secret_name},
                )
            else:
                logger.error(
                    _("A podman secret %(secret_name)s already exists."),
                    {"secret_name": secret_name},
                )
                return False
            podman_client.secrets.remove(secret_name)
            logger.info(
                _("Old podman secret %(secret_name)s was removed."),
                {"secret_name": secret_name},
            )
        podman_client.secrets.create(secret_name, secret_value)
        logger.info(
            _("New podman secret %(secret_name)s was set."),
            {"secret_name": secret_name},
        )
    return True
