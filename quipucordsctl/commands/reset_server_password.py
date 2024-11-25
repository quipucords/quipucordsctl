"""Reset the admin password."""

import argparse
import logging

logger = logging.getLogger(__name__)
NOT_A_COMMAND = True  # Until we complete the implementation.


def server_password_is_set() -> bool:
    """Check if the server password is already set."""
    # TODO `podman secret exists quipucords-server-password`
    return False


def run(args: argparse.Namespace) -> None:
    """Reset the server password."""
    logger.warning("%s is not yet implemented.", __name__)
    # TODO implement this.
    # TODO Should this also conditionally restart the server?
    # Old bash installer did the following:
    #   podman secret rm quipucords-server-password
    #   printf '%s' "${dsc_pass}" | podman secret create quipucords-server-password -
    #   podman secret ls --filter name=quipucords-server-password
    pass
