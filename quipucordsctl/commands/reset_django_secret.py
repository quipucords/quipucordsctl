"""Logic for the "reset_django_secret" command."""


def django_secret_is_set() -> bool:
    """Check if the Django secret key password is already set."""
    # TODO `podman secret exists quipucords-django-secret-key`
    return False


def run():
    """Reset the server password."""
    # TODO Implement this.
    # TODO Should this also conditionally restart the server?
    # Old bash installer did the following:
    #   podman secret rm quipucords-django-secret-key >/dev/null 2>&1 || true
    #   printf '%s' "$1" | podman secret create quipucords-django-secret-key -
    #   podman secret ls --filter name=quipucords-django-secret-key
    pass
