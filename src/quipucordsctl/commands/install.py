"""Install the server."""

import argparse
import configparser
import logging
import pathlib
import stat
import subprocess
import textwrap
import types
from datetime import datetime
from gettext import gettext as _

from quipucordsctl import podman_utils, settings, shell_utils, systemctl_utils
from quipucordsctl.commands import (
    reset_admin_password,
    reset_database_password,
    reset_encryption_secret,
    reset_redis_password,
    reset_session_secret,
)
from quipucordsctl.loginctl_utils import enable_linger
from quipucordsctl.systemdunitparser import SystemdUnitParser

INSTALL_SUCCESS_LONG_MESSAGE = _(
    textwrap.dedent(
        """
        Installation completed successfully. Please run the following commands to start the %(server_software_name)s server:

            podman login registry.redhat.io
            systemctl --user restart %(server_software_package)s-app
        """  # noqa: E501
    )
)

logger = logging.getLogger(__name__)


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Install the %(server_software_name)s server.") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            The `%(command_name)s` command configures and installs the
            %(server_software_name)s software on this system. The `%(command_name)s`
            command may prompt you to enter some required values, such as the admin
            login password, but you may set environment variables
            (e.g. `%(admin_password_env_var)s`) and/or use the global `--yes` and
            `--quiet` flags to bypass these required prompts.
            Please review the `--help` output for each of the `reset_*` commands for
            more details.
            The `%(command_name)s` command will setup Linger for the current user,
            this can be overridden with the `--no-linger` option.
            """
        )
    ) % {
        "command_name": __name__.rpartition(".")[-1],
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
        "admin_password_env_var": reset_admin_password.ENV_VAR_NAME,
    }


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-L",
        "--no-linger",
        action="store_true",
        help=_(
            "Do not automatically setup Linger for the current user"
            " (default: False, Linger will be enabled)",
        ),
    )


def mkdirs():
    """Ensure required data and config directories exist."""
    dir_paths = [
        settings.SERVER_ENV_DIR,
        settings.SYSTEMD_UNITS_DIR,
    ] + list(settings.SERVER_DATA_SUBDIRS.values())
    for dir_path in dir_paths:
        logger.debug(
            _("Ensuring directory exists: %(dir_path)s"),
            {"dir_path": dir_path},
        )
        dir_path.mkdir(parents=True, exist_ok=True)


# Each of the "reset secret" commands/modules implements a similar enough interface
# that allows the "install" command simply to iterate over each with the same calls.
# Note that we list the specific "reset" commands that the "install" command requires;
# we do not find them dynamically. Explicit is better than implicit, in this case.
_RESET_SECRETS_MODULE_ERROR_MESSAGE: dict[types.ModuleType, str] = {
    reset_encryption_secret: _(
        "The install command failed to reset encryption secret."
    ),
    reset_session_secret: _("The install command failed to reset session secret."),
    reset_admin_password: _("The install command failed to reset admin password."),
    reset_database_password: _(
        "The install command failed to reset database password."
    ),
    reset_redis_password: _("The install command failed to reset redis password."),
}


def reset_secrets(args: argparse.Namespace) -> bool:
    """Reset various secrets as part of the 'install' process."""
    for reset_secret_module, error in _RESET_SECRETS_MODULE_ERROR_MESSAGE.items():
        if not reset_secret_module.is_set() and not reset_secret_module.run(args):
            logger.error(error)
            return False
    return True


def get_override_conf_path(
    override_conf_dir: pathlib.Path | None, filename: str
) -> pathlib.Path | None:
    """Get the override configuration directory."""
    if not override_conf_dir:
        return None
    override_conf_path = override_conf_dir / filename
    if not override_conf_path.is_file():
        logger.debug(
            _("No override file found at: %(override_conf_path)s"),
            {"override_conf_path": override_conf_path},
        )
        return None
    try:
        if not override_conf_path.stat().st_mode & stat.S_IRUSR:
            logger.warning(
                _(
                    "Please check file permissions. "
                    "Cannot read override file at: %(override_conf_path)s"
                ),
                {"override_conf_path": override_conf_path},
            )
            return None
    except PermissionError:
        logger.warning(
            _(
                "Please check file permissions. "
                "Cannot access override file at: %(override_conf_path)s"
            ),
            {"override_conf_path": override_conf_path},
        )
        return None
    logger.debug(
        _("Override file found at: %(override_conf_path)s"),
        {"override_conf_path": override_conf_path},
    )
    return override_conf_path


def _update_systemd_template_config_with_overrides(
    template_filename: str,
    template_config: SystemdUnitParser,
    override_conf_path: pathlib.Path,
) -> None:
    """
    Update the given template_config with overrides found at override_conf_path.

    Note that this function treats template_config as a "pass by reference" parameter
    and updates its contents directly. This function returns nothing directly.
    """
    # Important note! Even though we could simply pass BOTH files
    # to SystemdUnitParser and expect it to merge them automatically,
    # when presented with list-like configs, SystemdUnitParser extends
    # the template's list with the override's list instead of replacing
    # it. In the old installer, we replace, and this somewhat complex
    # logic exists to mimic that "only replace" behavior.
    override_config = SystemdUnitParser()
    try:
        override_config.read(override_conf_path)
    except configparser.MissingSectionHeaderError:
        logger.warning(
            _(
                "Skipping overrides for %(template_filename)s due to missing section "
                "headers in your override file. Please check %(override_conf_path)s "
                "for any typos or errors."
            ),
            {
                "template_filename": template_filename,
                "override_conf_path": override_conf_path,
            },
        )

    for section in override_config.sections():
        for option in override_config.options(section):
            value = override_config.get(section, option)
            # template_config has a dict-like interface but is not a true dict. You
            # cannot call get() with defaults to find optional contents. The
            # following assign to old_value is conceptually like calling
            # "template_config.get(section, {}).get(option, None)" on true dicts.
            old_value = (
                template_config[section][option]
                if (
                    section in template_config.sections()  # section may not exist
                    and option in template_config[section]  # option may not exist
                )
                else None
            )
            logger.debug(
                _(
                    "Overriding %(template_filename)s %(section)s.%(option)s "
                    "from %(old_value)s to %(value)s"
                ),
                {
                    "template_filename": template_filename,
                    "section": section,
                    "option": option,
                    "old_value": old_value,
                    "value": value,
                },
            )
            template_config[section][option] = value


def write_systemd_unit(
    template_filename: str,
    override_conf_dir: pathlib.Path | None,
    destination_dir: pathlib.Path,
):
    """Write a systemd unit file by merging a template and optional override file."""
    template_path = shell_utils.systemd_template_dir() / template_filename
    template_config = SystemdUnitParser()
    template_config.read(template_path)

    if override_conf_path := get_override_conf_path(
        override_conf_dir, template_filename
    ):
        _update_systemd_template_config_with_overrides(
            template_filename, template_config, override_conf_path
        )

    destination = destination_dir / template_filename
    with destination.open("w") as destination_file:
        logger.info(
            _("Writing config to %(destination)s"),
            {"destination": destination.resolve()},
        )
        template_config.write(destination_file)


def write_env_file(
    template_filename: str,
    override_conf_dir: pathlib.Path | None,
    destination_dir: pathlib.Path,
):
    """Write an env file by merging a template and optional override file."""
    template_path = shell_utils.env_template_dir() / template_filename
    template_text = template_path.read_text(encoding="utf-8")

    if override_conf_path := get_override_conf_path(
        override_conf_dir, template_filename
    ):
        if override_text := override_conf_path.read_text(encoding="utf-8").strip():
            logger.debug(
                _(
                    "Appending overrides (%(line_count)s lines) "
                    "to template for %(template_filename)s before writing."
                ),
                {
                    "template_filename": template_filename,
                    "line_count": len(override_text.splitlines()),
                },
            )
            comment = _(
                "The following 'override' content was added "
                "by the user during installation at %(now)s"
            ) % {"now": datetime.now().isoformat()}
            template_text = f"{template_text}\n\n# {comment}\n\n{override_text}"
        else:
            logger.debug(
                _(
                    "Override file for %(template_filename)s "
                    "appears to be empty and will be skipped."
                ),
                {"template_filename": template_filename},
            )

    destination = destination_dir / template_filename
    logger.info(
        _("Writing config to %(destination)s"),
        {"destination": destination.resolve()},
    )
    destination.write_text(template_text)


def write_config_files(override_conf_dir: pathlib.Path | None = None):
    """Generate and write to disk all systemd unit and env files for the server."""
    logger.info("Generating config files")
    mkdirs()

    for filename in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        write_systemd_unit(
            filename,
            override_conf_dir=override_conf_dir,
            destination_dir=settings.SYSTEMD_UNITS_DIR,
        )
    for filename in settings.TEMPLATE_SERVER_ENV_FILENAMES:
        write_env_file(
            filename,
            override_conf_dir=override_conf_dir,
            destination_dir=settings.SERVER_ENV_DIR,
        )


def systemctl_reload():
    """Reload systemctl service to recognize new/updated units."""
    logger.info(
        _("Reloading systemctl to recognize %(server_software_name)s units"),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    shell_utils.run_command(settings.SYSTEMCTL_USER_RESET_FAILED_CMD)
    shell_utils.run_command(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD)


def run(args: argparse.Namespace) -> bool:
    """Install the server, ensuring requirements are met."""
    logger.debug("Starting install command")
    podman_utils.ensure_podman_socket()
    podman_utils.ensure_cgroups_v2()
    systemctl_utils.ensure_systemd_user_session()

    if not reset_secrets(args):
        return False

    override_conf_dir_path = None
    if args.override_conf_dir:
        if pathlib.Path(args.override_conf_dir).is_dir():
            override_conf_dir_path = pathlib.Path(args.override_conf_dir)
        else:
            logger.warning(
                _(
                    "The specified override configuration directory "
                    "('%(override_conf_dir)s') does not exist."
                ),
                {"override_conf_dir": args.override_conf_dir},
            )
    write_config_files(override_conf_dir_path)
    try:
        systemctl_reload()
    except subprocess.CalledProcessError:
        logger.error(_("systemctl reload failed unexpectedly. Please check logs."))
        return False

    if not enable_linger(args.no_linger):
        return False

    if not args.quiet:
        print(
            INSTALL_SUCCESS_LONG_MESSAGE
            % {
                "server_software_name": settings.SERVER_SOFTWARE_NAME,
                "server_software_package": settings.SERVER_SOFTWARE_PACKAGE,
            },
        )
    return True
