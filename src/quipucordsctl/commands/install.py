"""Install the server."""

import argparse
import logging
import pathlib
import stat
import subprocess
import textwrap
from datetime import datetime
from gettext import gettext as _
from importlib import resources

from quipucordsctl import podman_utils, settings, shell_utils
from quipucordsctl.commands import (
    reset_admin_password,
    reset_database_password,
    reset_encryption_secret,
    reset_redis_password,
    reset_session_secret,
)
from quipucordsctl.systemdunitparser import SystemdUnitParser

SYSTEMCTL_USER_RESET_FAILED_CMD = ["systemctl", "--user", "reset-failed"]
SYSTEMCTL_USER_DAEMON_RELOAD_CMD = ["systemctl", "--user", "daemon-reload"]

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


def write_systemd_unit(
    template_filename: str,
    override_conf_dir: pathlib.Path | None,
    destination_dir: pathlib.Path,
):
    """Write a systemd unit file by merging a template and optional override file."""
    template_traversable = resources.files("quipucordsctl").joinpath(
        f"{settings.TEMPLATE_SYSTEMD_UNITS_RESOURCE_PATH}/{template_filename}"
    )
    with resources.as_file(template_traversable) as template_path:
        template_config = SystemdUnitParser()
        template_config.read(template_path)

    if override_conf_path := get_override_conf_path(
        override_conf_dir, template_filename
    ):
        # Important note! Even though we could simply pass BOTH files
        # to SystemdUnitParser and expect it to merge them automatically,
        # when presented with list-like configs, SystemdUnitParser extends
        # the template's list with the override's list instead of replacing
        # it. In the old installer, we replace, and this somewhat complex
        # logic exists to mimic that "only replace" behavior.
        override_config = SystemdUnitParser()
        override_config.read(override_conf_path)
        for section in override_config.sections():
            for option in override_config.options(section):
                value = override_config.get(section, option)
                old_value = (
                    template_config[section][option]
                    if (
                        section in template_config.sections()
                        and option in template_config[section]
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
    template_traversable = resources.files("quipucordsctl").joinpath(
        f"{settings.TEMPLATE_SERVER_ENV_RESOURCE_PATH}/{template_filename}"
    )
    with resources.as_file(template_traversable) as template_path:
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
    shell_utils.run_command(SYSTEMCTL_USER_RESET_FAILED_CMD, quiet=True)
    shell_utils.run_command(SYSTEMCTL_USER_DAEMON_RELOAD_CMD, quiet=True)


def run(args: argparse.Namespace) -> bool:  # noqa: PLR0911
    """Install the server, ensuring requirements are met."""
    logger.debug("Starting install command")
    podman_utils.ensure_podman_socket()

    if (
        not reset_encryption_secret.encryption_secret_is_set()
        and not reset_encryption_secret.run(args)
    ):
        logger.error(_("The install command failed to reset encryption secret."))
        return False
    if (
        not reset_session_secret.session_secret_is_set()
        and not reset_session_secret.run(args)
    ):
        logger.error(_("The install command failed to reset session secret."))
        return False
    if (
        not reset_admin_password.admin_password_is_set()
        and not reset_admin_password.run(args)
    ):
        logger.error(_("The install command failed to reset admin password."))
        return False
    if (
        not reset_database_password.database_password_is_set()
        and not reset_database_password.run(args)
    ):
        logger.error(_("The install command failed to reset database password."))
        return False
    if (
        not reset_redis_password.redis_password_is_set()
        and not reset_redis_password.run(args)
    ):
        logger.error(_("The install command failed to reset Redis password."))
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

    if not args.quiet:
        print(
            INSTALL_SUCCESS_LONG_MESSAGE
            % {
                "server_software_name": settings.SERVER_SOFTWARE_NAME,
                "server_software_package": settings.SERVER_SOFTWARE_PACKAGE,
            },
        )
    return True
