"""Check that all necessary files and directories exist for running Quipucords."""

import argparse
import getpass
import logging
import os
import pathlib
import stat
import sys
from dataclasses import dataclass
from enum import Enum
from gettext import gettext as _
from typing import Optional

from quipucordsctl import settings

logger = logging.getLogger(__name__)


class StatusType(Enum):
    """Enumeration of possible path status types."""

    OK = "ok"
    BAD_PERMISSIONS = "bad_permissions"
    WRONG_OWNER = "wrong_owner"
    MISSING = "missing"


@dataclass
class PathCheckResult:
    """Result of checking a path's status."""

    status: StatusType
    path: pathlib.Path
    stat_info: Optional[os.stat_result] = None


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _(
        "Check that all necessary files and directories exist for running "
        "%(server_software_name)s."
    ) % {"server_software_name": settings.SERVER_SOFTWARE_NAME}


def check_directory_status(path: pathlib.Path) -> PathCheckResult:
    """
    Check the status of a directory.

    Returns:
        PathCheckResult with status indicating OK, bad permissions, wrong owner, or
        missing.
    """
    try:
        if not path.exists():
            return PathCheckResult(StatusType.MISSING, path)

        if not path.is_dir():
            return PathCheckResult(StatusType.MISSING, path)

        path_stat = path.stat()

        # Check ownership - should be owned by current user
        if path_stat.st_uid != os.getuid():
            return PathCheckResult(StatusType.WRONG_OWNER, path, path_stat)

        # Check permissions - should be readable and writable by owner
        mode = path_stat.st_mode
        if not (mode & stat.S_IRUSR and mode & stat.S_IWUSR):
            return PathCheckResult(StatusType.BAD_PERMISSIONS, path, path_stat)

        return PathCheckResult(StatusType.OK, path, path_stat)

    except PermissionError:
        return PathCheckResult(StatusType.BAD_PERMISSIONS, path)


def check_file_status(path: pathlib.Path) -> PathCheckResult:
    """
    Check the status of a file.

    Returns:
        PathCheckResult with status indicating OK, bad permissions, wrong owner, or
        missing.
    """
    try:
        if not path.exists():
            return PathCheckResult(StatusType.MISSING, path)

        if not path.is_file():
            return PathCheckResult(StatusType.MISSING, path)

        path_stat = path.stat()

        # Check ownership - should be owned by current user
        if path_stat.st_uid != os.getuid():
            return PathCheckResult(StatusType.WRONG_OWNER, path, path_stat)

        # Check permissions - should be readable and writable by owner
        mode = path_stat.st_mode
        if not (mode & stat.S_IRUSR and mode & stat.S_IWUSR):
            return PathCheckResult(StatusType.BAD_PERMISSIONS, path, path_stat)

        return PathCheckResult(StatusType.OK, path, path_stat)

    except PermissionError:
        return PathCheckResult(StatusType.BAD_PERMISSIONS, path)


def _log_ok_status(result: PathCheckResult) -> None:
    """Log OK status with detailed info if available."""
    try:
        if result.stat_info:
            logger.info(
                _("%(path)s: OK: %(perms)s %(owner)s"),
                {
                    "path": result.path,
                    "perms": stat.filemode(result.stat_info.st_mode),
                    "owner": result.path.owner(),
                },
            )
            return
    except (OSError, KeyError) as error:
        logger.error(
            _("Unexpected error reporting status of %(path)s: %(error)s"),
            {"path": result.path, "error": error},
        )
    logger.info(_("%(path)s: OK"), {"path": result.path})


def _log_bad_permissions_status(result: PathCheckResult) -> None:
    """Log bad permissions status with detailed info if available."""
    try:
        if result.stat_info:
            logger.error(
                _("%(path)s: ERROR: Incorrect permission(s): %(perms)s"),
                {
                    "path": result.path,
                    "perms": stat.filemode(result.stat_info.st_mode),
                },
            )
            return
    except OSError as error:
        logger.error(
            _("Unexpected error reporting status of %(path)s: %(error)s"),
            {"path": result.path, "error": error},
        )
    logger.error(_("%(path)s: ERROR: Incorrect permissions"), {"path": result.path})


def _log_wrong_owner_status(result: PathCheckResult) -> None:
    """Log wrong owner status with detailed info if available."""
    try:
        if result.stat_info:
            logger.error(
                _(
                    "%(path)s: ERROR: Not owned by you (incorrect ownership): "
                    "%(uid)s %(owner)s"
                ),
                {
                    "path": result.path,
                    "user": getpass.getuser(),
                    "uid": result.stat_info.st_uid,
                    "owner": result.path.owner(),
                },
            )
            return
    except (OSError, KeyError) as error:
        logger.error(
            _("Unexpected error reporting status of %(path)s: %(error)s"),
            {"path": result.path, "error": error},
        )
    logger.error(
        _("%(path)s: ERROR: Not owned by you (incorrect ownership)"),
        {"path": result.path},
    )


def log_path_status(result: PathCheckResult) -> None:
    """Print the status of a path in a user-friendly format."""
    if result.status == StatusType.OK:
        _log_ok_status(result)
    elif result.status == StatusType.BAD_PERMISSIONS:
        _log_bad_permissions_status(result)
    elif result.status == StatusType.WRONG_OWNER:
        _log_wrong_owner_status(result)
    elif result.status == StatusType.MISSING:
        logger.error(_("%(path)s: ERROR: Missing"), {"path": result.path})
    else:
        logger.error(_("%(path)s: ERROR: Unknown status"), {"path": result.path})


def check_directory_and_print_status(path: pathlib.Path) -> bool:
    """Check a directory status and print the result.

    Returns True if OK, False if there's an issue.
    """
    result = check_directory_status(path)
    log_path_status(result)
    return result.status == StatusType.OK


def check_file_and_print_status(path: pathlib.Path) -> bool:
    """Check a file status and print the result.

    Returns True if OK, False if there's an issue.
    """
    result = check_file_status(path)
    log_path_status(result)
    return result.status == StatusType.OK


def _check_data_directories() -> int:
    """Check main data directory and subdirectories. Returns error count."""
    error_count = 0

    # Check main data directory
    if not check_directory_and_print_status(settings.SERVER_DATA_DIR):
        error_count += 1

    # Check data subdirectories
    for subdir_path in settings.SERVER_DATA_SUBDIRS.values():
        if not check_directory_and_print_status(subdir_path):
            error_count += 1

    # Check database userdata directory (special case)
    db_userdata_dir = settings.SERVER_DATA_DIR / "db" / "userdata"
    if not check_directory_and_print_status(db_userdata_dir):
        error_count += 1

    return error_count


def _check_required_files() -> int:
    """Check specific files that should exist. Returns error count."""
    error_count = 0

    specific_files = [
        settings.SERVER_DATA_DIR / "certs" / "server.key",
        settings.SERVER_DATA_DIR / "certs" / "server.crt",
    ]

    for file_path in specific_files:
        if not check_file_and_print_status(file_path):
            error_count += 1

    return error_count


def _check_configuration_directories() -> int:
    """Check configuration directories. Returns error count."""
    error_count = 0

    if not check_directory_and_print_status(settings.SERVER_ENV_DIR):
        error_count += 1

    if not check_directory_and_print_status(settings.SYSTEMD_UNITS_DIR):
        error_count += 1

    return error_count


def _check_configuration_files() -> int:
    """Check environment and systemd unit files. Returns error count."""
    error_count = 0

    # Check environment files
    for env_filename in settings.TEMPLATE_SERVER_ENV_FILENAMES:
        env_file_path = settings.SERVER_ENV_DIR / env_filename
        if not check_file_and_print_status(env_file_path):
            error_count += 1

    # Check systemd unit files
    for unit_filename in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        unit_file_path = settings.SYSTEMD_UNITS_DIR / unit_filename
        if not check_file_and_print_status(unit_file_path):
            error_count += 1

    return error_count


def run(args: argparse.Namespace) -> bool:
    """Run the check command."""
    logger.info(
        _("Checking %(server_software_name)s setup and configurations..."),
        {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )

    error_count = 0
    error_count += _check_data_directories()
    error_count += _check_required_files()
    error_count += _check_configuration_directories()
    error_count += _check_configuration_files()

    # Return success if no errors, otherwise exit with count of issues
    # This matches the acceptance criteria: "returns 0 on success or the positive
    # number of unexpected states it encountered"
    if error_count == 0:
        logger.info(_("All checks passed successfully."))
        return True
    else:
        logger.error(_("Found %(error_count)d issues."), {"error_count": error_count})
        sys.exit(error_count)
