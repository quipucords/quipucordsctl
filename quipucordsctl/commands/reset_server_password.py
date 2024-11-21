"""Logic for the "reset_server_password" command."""


def server_password_is_set(verbose: bool = False) -> bool:
    """Check if the server password is already set."""
    # TODO `podman secret exists quipucords-server-password`
    return False


def run(verbose: bool = False):
    """Reset the server password."""
    # TODO implement this.
    # TODO Should this also conditionally restart the server?
    # Old bash installer did the following:
    #   podman secret rm quipucords-server-password
    #   printf '%s' "${dsc_pass}" | podman secret create quipucords-server-password -
    #   podman secret ls --filter name=quipucords-server-password
    pass
