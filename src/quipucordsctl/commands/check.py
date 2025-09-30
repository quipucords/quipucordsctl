"""Check that all necessary files and directories exist for running Quipucords."""

import argparse
import logging
import os
import pathlib
import stat
import sys
from gettext import gettext as _

from quipucordsctl import settings

logger = logging.getLogger(__name__)


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Check that all necessary files and directories exist for running %(server_software_name)s.") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    }


def check_directory_status(path: pathlib.Path) -> int:
    """
    Check the status of a directory.
    
    Returns:
        0: OK (exists, owned by user, readable & writable)
        1: Bad permissions (exists but wrong permissions)
        2: Not owned by user (exists but wrong owner)
        3: Missing (doesn't exist)
    """
    try:
        if not path.exists():
            return 3  # Missing
        
        if not path.is_dir():
            return 3  # Not a directory, treat as missing
        
        path_stat = path.stat()
        
        # Check ownership - should be owned by current user
        if path_stat.st_uid != os.getuid():
            return 2  # Not owned by you
        
        # Check permissions - should be readable and writable by owner
        mode = path_stat.st_mode
        if not (mode & stat.S_IRUSR and mode & stat.S_IWUSR):
            return 1  # Bad permissions
        
        return 0  # OK
        
    except PermissionError:
        return 1  # Bad permissions


def check_file_status(path: pathlib.Path) -> int:
    """
    Check the status of a file.
    
    Returns:
        0: OK (exists, owned by user, readable & writable)
        1: Bad permissions (exists but wrong permissions)
        2: Not owned by user (exists but wrong owner)
        3: Missing (doesn't exist)
    """
    try:
        if not path.exists():
            return 3  # Missing
        
        if not path.is_file():
            return 3  # Not a file, treat as missing
        
        path_stat = path.stat()
        
        # Check ownership - should be owned by current user
        if path_stat.st_uid != os.getuid():
            return 2  # Not owned by you
        
        # Check permissions - should be readable and writable by owner
        mode = path_stat.st_mode
        if not (mode & stat.S_IRUSR and mode & stat.S_IWUSR):
            return 1  # Bad permissions
        
        return 0  # OK
        
    except PermissionError:
        return 1  # Bad permissions


def print_path_status(status: int, path: pathlib.Path) -> None:
    """Print the status of a path in a user-friendly format."""
    if status == 0:
        try:
            path_stat = path.stat()
            perms_owner = oct(path_stat.st_mode)[-3:] + f" {path.owner()}"
            logger.info("%(path)s: OK: %(perms_owner)s", {
                "path": path,
                "perms_owner": perms_owner
            })
        except (OSError, KeyError):
            logger.info("%(path)s: OK", {"path": path})
    elif status == 1:
        try:
            path_stat = path.stat()
            perms = f"{oct(path_stat.st_mode)[-3:]} {oct(path_stat.st_mode)}"
            logger.error("%(path)s: ERROR: Incorrect permission(s): %(perms)s", {
                "path": path,
                "perms": perms
            })
        except OSError:
            logger.error("%(path)s: ERROR: Incorrect permissions", {"path": path})
    elif status == 2:
        try:
            path_stat = path.stat()
            owner = f"{path_stat.st_uid} {path.owner()}"
            logger.error("%(path)s: ERROR: Not owned by you (incorrect ownership): %(owner)s", {
                "path": path,
                "owner": owner
            })
        except (OSError, KeyError):
            logger.error("%(path)s: ERROR: Not owned by you (incorrect ownership)", {"path": path})
    elif status == 3:
        logger.error("%(path)s: ERROR: Missing", {"path": path})
    else:
        logger.error("%(path)s: ERROR: Unknown status", {"path": path})


def check_directory_and_print_status(path: pathlib.Path) -> int:
    """Check a directory status and print the result."""
    status = check_directory_status(path)
    print_path_status(status, path)
    return status


def check_file_and_print_status(path: pathlib.Path) -> int:
    """Check a file status and print the result."""
    status = check_file_status(path)
    print_path_status(status, path)
    return status


def run(args: argparse.Namespace) -> bool:
    """Run the check command."""
    logger.info("Checking %(server_software_name)s setup and configurations...", {
        "server_software_name": settings.SERVER_SOFTWARE_NAME
    })
    
    error_count = 0
    
    # Check main data directory
    if check_directory_and_print_status(settings.SERVER_DATA_DIR) != 0:
        error_count += 1
    
    # Check data subdirectories
    for subdir_path in settings.SERVER_DATA_SUBDIRS.values():
        if check_directory_and_print_status(subdir_path) != 0:
            error_count += 1
    
    # Check specific files that should exist
    specific_files = [
        settings.SERVER_DATA_DIR / "certs" / "server.key",
        settings.SERVER_DATA_DIR / "certs" / "server.crt",
        settings.SERVER_DATA_DIR / "data" / "secret.txt",
    ]
    
    for file_path in specific_files:
        if check_file_and_print_status(file_path) != 0:
            error_count += 1
    
    # Check database userdata directory (special case - it's a directory under db)
    db_userdata_dir = settings.SERVER_DATA_DIR / "db" / "userdata"
    if check_directory_and_print_status(db_userdata_dir) != 0:
        error_count += 1
    
    # Check configuration directories
    if check_directory_and_print_status(settings.SERVER_ENV_DIR) != 0:
        error_count += 1
    
    if check_directory_and_print_status(settings.SYSTEMD_UNITS_DIR) != 0:
        error_count += 1
    
    # Check environment files
    for env_filename in settings.TEMPLATE_SERVER_ENV_FILENAMES:
        env_file_path = settings.SERVER_ENV_DIR / env_filename
        if check_file_and_print_status(env_file_path) != 0:
            error_count += 1
    
    # Check systemd unit files
    for unit_filename in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        unit_file_path = settings.SYSTEMD_UNITS_DIR / unit_filename
        if check_file_and_print_status(unit_file_path) != 0:
            error_count += 1
    
    # Return success if no errors, otherwise exit with count of issues
    # This matches the acceptance criteria: "returns 0 on success or the positive number of unexpected states it encountered"
    if error_count == 0:
        logger.info("All checks passed successfully.")
        return True
    else:
        logger.error("Found %(error_count)d issues.", {"error_count": error_count})
        sys.exit(error_count)
