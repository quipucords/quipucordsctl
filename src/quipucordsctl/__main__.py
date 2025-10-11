"""Package command-line entrypoint."""

import gettext
import importlib.resources as pkg_resources
import sys

from quipucordsctl import shell_utils


def set_up_gettext():
    """Set up gettext for string localization."""
    locale_path = pkg_resources.files("quipucordsctl").joinpath("locale")
    gettext.bindtextdomain("messages", localedir=str(locale_path))


def main():
    """Run command-line entrypoint."""
    set_up_gettext()

    # For RPM installs, before we import cli, we need to make sure podman
    # is installed for the running python interpreter.
    #
    # Note: while we have the dependency on python3-podman in our rpm, in
    #       RHEL-8 and RHEL-9 platforms, python3-podman is built against
    #       the core OS Python version which is an earlier version than the
    #       python 3.12 we require.
    if shell_utils.is_rpm_exec():
        shell_utils.run_command([sys.executable, "-m", "ensurepip"])
        shell_utils.run_command(
            [sys.executable, "-m", "pip", "-q", "install", "podman"]
        )

    # We must run set_up_gettext **before** we import anything else.
    # This helps to guarantee that gettext shared state/globals use
    # our specific bindtextdomain contents.
    from . import cli  # noqa: PLC0415

    cli.run()


if __name__ == "__main__":
    main()
