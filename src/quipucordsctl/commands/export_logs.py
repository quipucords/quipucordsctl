"""Export container logs."""

import argparse
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
from datetime import datetime
from gettext import gettext as _
from pathlib import Path

from quipucordsctl import argparse_utils, settings, shell_utils

logger = logging.getLogger(__name__)
BUFSIZE = 5 * 1024 * 1024  # 5 MB


def get_display_group() -> argparse_utils.DisplayGroups:
    """Get the group identifier for displaying this command in CLI help text."""
    return argparse_utils.DisplayGroups.DIAGNOSTICS


class PreconditionsNotMetError(Exception):
    """Raised if user wants us to create a file we can't."""


def get_help() -> str:
    """Get the help/docstring for this command."""
    return _("Export %(server_software_name)s logs") % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
    }


def get_description() -> str:
    """Get the longer description of this command."""
    return _(
        textwrap.dedent(
            """
            Export %(server_software_name)s logs and save to a single compressed
            `.tar.gz` file. If you open a support case to get help with
            %(server_software_name)s, you may need to provide this file.
            """
        )
    ) % {
        "server_software_name": settings.SERVER_SOFTWARE_NAME,
    }


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Add arguments to this command's argparse subparser."""
    parser.add_argument(
        "-o",
        "--output",
        default=Path(),
        type=Path,
        help=_(
            "Path to directory where logs archive will be created "
            "(default: current working directory)"
        ),
    )


def check_preconditions(dest: Path) -> bool:
    """Check if path provided by user is a directory where we can create a new file."""
    if not dest.is_dir():
        logger.error(
            _("Must be a directory: %(path)s"), {"path": dest.resolve().as_posix()}
        )
        return False

    if not os.access(dest, os.R_OK | os.W_OK):
        logger.error(
            _("Directory %(path)s must be readable and writable"),
            {"path": dest.resolve().as_posix()},
        )
        return False

    return True


def copytree_helper(source: Path, dest: Path):
    """Run shutil.copytree, but handle problems gracefully."""
    try:
        shutil.copytree(source, dest, symlinks=False)
    except shutil.Error as e:
        msg = _(
            "Failed to copy some files from %(filepath)s. Logs may not be complete."
        )
        logger.error(msg, {"filepath": source.resolve().as_posix()})
        details = (ed[-1] for ed in e.args[0])
        logger.debug("\n".join(details))
    except FileNotFoundError:
        # source does not exist. This is expected if user has trouble starting
        # services.
        # FIXME: Should we check is service is running and report then?
        pass


def export_container_logs(dest: Path):
    """Export Quipucords logs into files inside a directory."""
    for service in settings.SYSTEMD_SERVICE_FILENAMES:
        logger.info(_("Exporting logs for %(service_name)s"), {"service_name": service})
        fname = Path(service).stem
        command = ["journalctl", f"--user-unit={service}"]
        try:
            dest_filename = (dest / "j.log").with_stem(fname)
            with dest_filename.open("w") as fh:
                shell_utils.run_command(
                    command,
                    # TODO should next one be user-configurable?
                    wait_timeout=settings.DEFAULT_JOURNALCTL_WAIT_TIMEOUT,
                    bufsize=BUFSIZE,
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                )
        except OSError as e:
            msg = _(
                "Failed to save logs for %(service_name)s to %(filepath)s. "
                "Exported logs may be incomplete."
            )
            logger.error(
                msg,
                {
                    "filepath": dest_filename.resolve().as_posix(),
                    "service_name": service,
                },
            )
            logger.debug(e)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            # run_command already prints the relevant messages. We just tell the user
            # logs may not be complete and continue in a vain hope that was
            # intermittent issue and we can still export something.
            msg = _(
                "Failed to export logs for %(service_name)s. "
                "Exported logs may be incomplete."
            )
            logger.error(msg, {"service_name": service})


def copy_qpc_log(dest: Path):
    """Copy qpc (CLI) log file. Note the path is the same upstream and downstream."""
    source = (settings.SERVER_DATA_DIR / "../qpc/qpc.log").resolve()
    try:
        shutil.copy(source, dest, follow_symlinks=True)
    except FileNotFoundError:
        logger.warning(
            _(
                "File not found: %(filepath)s. "
                "%(server_software_name)s CLI has not written any logs, "
                "or exported logs may be incomplete.",
            ),
            {
                "server_software_name": settings.SERVER_SOFTWARE_NAME,
                "filepath": source.as_posix(),
            },
        )
    except PermissionError as e:
        logger.error(
            _(
                "Permission denied trying to access %(filepath)s. "
                "Permissions may be incorrect, and exported logs may be incomplete."
            ),
            {
                "filepath": source.as_posix(),
            },
        )
        logger.debug(e)


def copy_postgres_logs(dest: Path):
    """Copy Postgres log files."""
    source = settings.SERVER_DATA_DIR / "db/userdata/log/"
    actual_dest = dest / "postgres"
    copytree_helper(source, actual_dest)


def copy_nginx_logs(dest: Path):
    """Copy nginx log files."""
    source = settings.SERVER_DATA_DIR / "log/nginx/"
    actual_dest = dest / "nginx"
    copytree_helper(source, actual_dest)


def prepare_export_directory(dest: Path):
    """Prepare directory with all the logs that will be put in archive."""
    export_container_logs(dest)
    copy_qpc_log(dest)
    copy_postgres_logs(dest)
    copy_nginx_logs(dest)


def run(args: argparse.Namespace) -> bool:
    """
    Export container logs to a file in a directory specified by the user.

    Fail early and loudly if user provided a path to a file or directory
    that is not writable.
    """
    if not check_preconditions(args.output):
        return False

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    software_name = settings.SERVER_SOFTWARE_PACKAGE
    dest_file = args.output / f"{software_name}-logs-{timestamp}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="qpc-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        prepare_export_directory(tmpdir_path)

        if not any(c.is_file() for c in tmpdir_path.rglob("*")):
            msg = _(
                "Failed to obtain any logs. See errors above. "
                "Archive will not be created."
            )
            logger.error(msg)
            return False

        with tarfile.open(name=dest_file, mode="w:gz") as tar:
            tar.add(tmpdir, arcname=f"{software_name}-logs")

    logger.info(_("Exported logs to %(dest_file)s"), {"dest_file": dest_file})
    return True
