"""Utilities for interacting with user's shell and external programs."""

import subprocess
import sys
from gettext import gettext as _


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
