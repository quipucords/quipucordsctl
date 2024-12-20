"""Reset the Django secret key."""

import argparse
import logging

logger = logging.getLogger(__name__)
NOT_A_COMMAND = True  # Until we complete the implementation.


def django_secret_is_set() -> bool:
    """Check if the Django secret key password is already set."""
    # TODO `podman secret exists quipucords-django-secret-key`
    return False


def run(args: argparse.Namespace) -> None:
    """Reset the server password."""
    logger.warning("%s is not yet implemented.", __name__)
    # TODO Implement this.
    # TODO Should this also conditionally restart the server?
    # Old bash installer did the following:
    #   podman secret rm quipucords-django-secret-key >/dev/null 2>&1 || true
    #   printf '%s' "$1" | podman secret create quipucords-django-secret-key -
    #   podman secret ls --filter name=quipucords-django-secret-key
    pass
