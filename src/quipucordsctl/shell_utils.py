"""Utilities for interacting with user's shell and external programs."""

import logging
import subprocess
from gettext import gettext as _

logger = logging.getLogger(__name__)


def confirm(prompt: str | None = None) -> bool:
    """Present a typical [y/n] confirmation prompt."""
    user_input = None
    if not prompt:
        prompt = _("Do you want to continue? [y/n] ")
    while user_input is None:
        user_input = input(prompt).lower()
        if user_input == _("y"):
            return True
        elif user_input != _("n"):
            print(_("Please answer with 'y' or 'n'."))
            user_input = None
    return False


def run_command(command: list[str], *, quiet=False) -> tuple[str, str, int]:
    """Run an external program."""
    logger.debug(
        _("Invoking subprocess with arguments %(command)s"), {"command": command}
    )
    try:
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
    except Exception as error:
        logger.error(
            _("Subprocess with arguments %(command)s failed due to unexpected error."),
            {"command": command},
        )
        raise error

    stdout, stderr = stdout.strip(), stderr.strip()
    # If the command failed, log the output despite quite arg.
    if stdout and (not quiet or exit_code != 0):
        for line in stdout.splitlines():
            logger.debug(line)
    if stderr and (not quiet or exit_code != 0):
        for line in stderr.splitlines():
            logger.warning(line)
    if exit_code != 0:
        logger.error(
            _(
                "Subprocess with arguments %(command)s failed "
                "with exit code %(exit_code)s"
            ),
            {"command": command, "exit_code": exit_code},
        )
        raise subprocess.CalledProcessError(exit_code, command, stdout, stderr)

    return stdout, stderr, exit_code
