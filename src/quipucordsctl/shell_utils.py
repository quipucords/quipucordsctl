"""Utilities for interacting with user's shell and external programs."""

import logging
import os
import pathlib
import shlex
import subprocess
import sys
from gettext import gettext as _
from importlib import resources

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


def is_rpm_exec() -> bool:
    """Return True if we're running the RPM installed command."""
    rpm_installed_exec = f"/usr/bin/{settings.PROGRAM_NAME}"
    if pathlib.Path(rpm_installed_exec).exists():
        return pathlib.Path(sys.argv[0]).samefile(rpm_installed_exec)
    return False


def template_dir() -> pathlib.Path:
    """Return the template directory for the running command."""
    if is_rpm_exec():
        return pathlib.Path(f"/usr/share/{settings.PROGRAM_NAME}")
    else:
        return pathlib.Path(str(resources.files("quipucordsctl").joinpath("templates")))


def systemd_template_dir() -> pathlib.Path:
    """Return the systemd template directory for the running command."""
    return template_dir().joinpath("config")


def env_template_dir() -> pathlib.Path:
    """Return the env template directory for the running command."""
    return template_dir().joinpath("env")


def run_command(
    command: list[str],
    *,
    raise_error: bool = True,
    wait_timeout: int | None = None,
    stdin: str | None = None,
) -> tuple[str, str, int]:
    """Run an external program."""
    if not all(isinstance(arg, str) for arg in command):
        raise TypeError(_("Command arguments must be strings. Got: %r") % command)
    logger.debug(_("Invoking subprocess: %s"), " ".join(map(shlex.quote, command)))
    if wait_timeout is None:
        wait_timeout = settings.DEFAULT_SUBPROCESS_WAIT_TIMEOUT
        logger.debug(
            _("Command has %(wait_timeout)s seconds timeout."),
            {"wait_timeout": wait_timeout},
        )
    try:
        process = subprocess.Popen(
            args=command,  # a list like ["systemctl", "--user", "reset-failed"]
            stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # we always expect input/output text, not byte strings
            shell=False,  # redundant, but a safe precaution in case defaults change
        )

        # TODO figure out how we want to handle stdout/stderr
        # TODO maybe support "realtime" stdout display instead of capturing at the end
        # TODO should these *always* go to our stdout/stderr or use the logger?
        stdout, stderr = process.communicate(input=stdin, timeout=wait_timeout)
        exit_code = process.returncode
    except subprocess.TimeoutExpired as error:
        logger.error(
            _(
                "Subprocess with arguments %(command)s timed out after "
                "%(wait_timeout)s seconds."
            ),
            {"command": command, "wait_timeout": wait_timeout},
        )
        raise error
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

    if raise_error and exit_code != 0:
        logger.error(
            _(
                "Subprocess with arguments %(command)s failed "
                "with exit code %(exit_code)s"
            ),
            {"command": command, "exit_code": exit_code},
        )
        raise subprocess.CalledProcessError(exit_code, command, stdout, stderr)

    return stdout, stderr, exit_code
