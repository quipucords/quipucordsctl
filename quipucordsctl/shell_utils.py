"""Utilities for interacting with user's shell and external programs."""

import functools
import subprocess
import sys
from gettext import gettext as _

from podman import PodmanClient

MACOS_DEFAULT_PODMAN_URL = "unix:///var/run/docker.sock"


def confirm(prompt: str | None = None) -> bool:
    """Present a typical [y/n] confirmation prompt."""
    user_input = None
    if not prompt:
        prompt = _("Do you want to continue? [y/n] ")
    while user_input is None:
        user_input = input(prompt).lower()
        if user_input == "y":
            return True
        elif user_input != "n":
            print(_("Please answer with 'y' or 'n'."))
            user_input = None
    return False


@functools.cache
def get_podman_client(base_url=None) -> PodmanClient:
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
    return PodmanClient(**kwargs)


def run_command(command: list[str]) -> tuple[str, str, int]:
    """Run an external program."""
    process = subprocess.Popen(
        args=command,  # a list like ["systemctl", "--user", "reset-failed"]
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,  # we always expect input/output text, not byte strings
    )

    # TODO figure out how we want to handle stdout/stderr
    # TODO maybe support "realtime" stdout display instead of capturing at the end
    # TODO should these *always* go to our stdout/stderr or use the logger?
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    stdout, stderr = stdout.strip(), stderr.strip()
    if stdout:
        print(f"stdout: {stdout}")
    if stderr:
        print(stderr, file=sys.stderr)
    if exit_code != 0:
        raise subprocess.CalledProcessError(exit_code, command)

    return stdout, stderr, exit_code
