"""Utilities for interacting with user's shell and external programs."""

import logging
import os
import subprocess
from gettext import gettext as _

from quipucordsctl import settings

logger = logging.getLogger(__name__)


def get_env(name: str) -> str | None:
    """Get the value of the specified environment variable."""
    if value := os.environ.get(name):
        logger.debug(_("Environment variable '%(name)s' found."), {"name": name})
        return value
    else:
        logger.debug(_("Environment variable '%(name)s' not found."), {"name": name})
        return None


def confirm(prompt: str | None = None) -> bool:
    """Present a typical [y/n] confirmation prompt."""
    if settings.runtime.yes:
        return True
    if settings.runtime.quiet:
        return False

    user_input = None
    if not prompt:
        prompt = _("Do you want to continue?")
    while user_input is None:
        prompt_with_yn = _("%(question)s [y/n] ") % {"question": prompt}
        user_input = input(prompt_with_yn).lower()
        if user_input == _("y"):
            return True
        elif user_input != _("n"):
            print(_("Please answer with 'y' or 'n'."))
            user_input = None
    return False


def run_command(command: list[str]) -> tuple[str, str, int]:
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

    # make stdout and stderr noisier if the process did not exit cleanly
    stdout_logger = logger.debug if exit_code == 0 else logger.info
    stderr_logger = logger.debug if exit_code == 0 else logger.error
    for line in stdout.strip().splitlines():
        stdout_logger(line)
    for line in stderr.strip().splitlines():
        stderr_logger(line)

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
