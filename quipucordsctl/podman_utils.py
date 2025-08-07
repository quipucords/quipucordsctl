"""Functions to simplify interfacing with podman."""

import functools
import logging
import sys
from gettext import gettext as _

import podman

logger = logging.getLogger(__name__)
MACOS_DEFAULT_PODMAN_URL = "unix:///var/run/docker.sock"


@functools.cache
def get_podman_client(base_url=None) -> podman.PodmanClient:
    """Get a podman client."""
    # podman on macOS/darwin requires a different default base_url,
    # and we should also allow the caller to specify their own.
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
