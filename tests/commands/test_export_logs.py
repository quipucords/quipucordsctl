"""Test the "export_logs" command."""

import itertools
import logging
import pathlib
import subprocess
import tarfile
from unittest import mock

import pytest

from quipucordsctl import settings
from quipucordsctl.commands import export_logs


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(export_logs, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


@pytest.fixture
def archive_dir(tmp_path: pathlib.Path):
    """Create and return a directory in tmp_path that will act as dest."""
    archive = tmp_path / "archive_dir"
    archive.mkdir()
    yield archive


def test_get_help():
    """Test the get_help returns an appropriate string."""
    assert f"Export {settings.SERVER_SOFTWARE_NAME} logs" == export_logs.get_help()


def test_get_description():
    """Test the get_description returns an appropriate string."""
    assert (
        f"Export {settings.SERVER_SOFTWARE_NAME} logs and save"
        in export_logs.get_description()
    )


def test_run_happy_path(tmp_path: pathlib.Path):
    """Test the run command happy path."""
    mock_args = mock.Mock()
    mock_args.output = tmp_path
    log_name = "server.log"
    expected_archived = f"{settings.SERVER_SOFTWARE_PACKAGE}-logs/{log_name}"

    def mock_prepare_export_directory(dest: pathlib.Path):
        (dest / log_name).touch()

    with mock.patch.object(
        export_logs, "prepare_export_directory", mock_prepare_export_directory
    ):
        run_res = export_logs.run(mock_args)
        assert run_res is True

    for file in tmp_path.glob("*.tar.gz"):
        assert file.name.startswith(f"{settings.SERVER_SOFTWARE_PACKAGE}-logs")
        with tarfile.open(file) as tar:
            # will raise uncaught KeyError if file is not in archive
            tar.getmember(expected_archived)
        break
    else:
        assert False, "logs archive was not created"


def test_run_output_is_not_dir(tmp_path: pathlib.Path, caplog):
    """Test the run command - output is not a directory."""
    caplog.set_level(logging.ERROR)
    output = tmp_path / "some.file"
    output.touch()
    mock_args = mock.Mock()
    mock_args.output = output

    assert export_logs.run(mock_args) is False
    assert "must be a directory" in caplog.text


@pytest.mark.parametrize("mode", [0o000, 0o100, 0o200, 0o300, 0o400, 0o500, 0o600])
def test_run_output_lacks_expected_modes(mode, tmp_path: pathlib.Path, caplog):
    """Test export_logs checks required permissions/modes of output directory."""
    caplog.set_level(logging.ERROR)
    output = tmp_path / "new-dir"
    output.mkdir(mode=mode)
    mock_args = mock.Mock()
    mock_args.output = output

    assert export_logs.run(mock_args) is False
    assert "must be readable, writable, and executable" in caplog.text


def test_run_no_exported_files(tmp_path: pathlib.Path, caplog):
    """Test the run command fails if no files were archived."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.output = tmp_path

    with mock.patch.object(export_logs, "prepare_export_directory", lambda _: None):
        run_res = export_logs.run(mock_args)
        assert run_res is False
        assert "Failed to obtain any logs." in caplog.text

    for file in tmp_path.glob("*.tar.gz"):
        assert not file, "logs archive was unexpectedly created"


def test_export_container_logs_happy_path(tmp_path: pathlib.Path, mock_shell_utils):
    """Test happy path for export_container_logs: command is run for each service."""
    export_logs.export_container_logs(tmp_path)

    assert mock_shell_utils.run_command.call_count == len(
        settings.SYSTEMD_SERVICE_FILENAMES
    )

    expected_calls = []
    for service in settings.SYSTEMD_SERVICE_FILENAMES:
        expected_calls.append(
            mock.call(
                ["journalctl", f"--user-unit={service}"],
                wait_timeout=mock.ANY,
                bufsize=mock.ANY,
                stdout=mock.ANY,
                stderr=subprocess.STDOUT,
            )
        )
    mock_shell_utils.run_command.assert_has_calls(expected_calls, any_order=True)


def test_export_container_logs_file_open_error(
    tmp_path: pathlib.Path, caplog, mock_shell_utils
):
    """Test export_container_logs can handle OSError."""
    caplog.set_level(logging.ERROR)
    first_service = settings.SYSTEMD_SERVICE_FILENAMES[0]
    first_service_stem = pathlib.Path(first_service).stem
    other_services = settings.SYSTEMD_SERVICE_FILENAMES[1:]

    mock_opener = mock.mock_open()

    def mock_open_impl(self, *args, **kwargs):
        if self.stem == first_service_stem:
            raise OSError("Mocked OSError during file creation")
        return mock_opener(self, *args, **kwargs)

    with mock.patch.object(pathlib.Path, "open", mock_open_impl):
        export_logs.export_container_logs(tmp_path)

        # Check that the first service failed due to OSError
        logged_path = (
            (tmp_path / "p.log").with_stem(first_service_stem).resolve().as_posix()
        )
        assert "Exported logs may be incomplete." in caplog.text
        assert logged_path in caplog.text

        # Check other services passed open call
        expected_calls = []
        for service in other_services:
            expected_calls.append(
                mock.call(
                    ["journalctl", f"--user-unit={service}"],
                    wait_timeout=mock.ANY,
                    bufsize=mock.ANY,
                    stdout=mock.ANY,
                    stderr=subprocess.STDOUT,
                )
            )
        assert mock_shell_utils.run_command.call_count == len(other_services)
        mock_shell_utils.run_command.assert_has_calls(expected_calls)


def test_export_container_logs_journalctl_failure(
    tmp_path: pathlib.Path, caplog, mock_shell_utils
):
    """Test export_container_logs handles journalctl call failure."""
    caplog.set_level(logging.ERROR)

    mock_shell_utils.run_command.side_effect = itertools.chain(
        [subprocess.CalledProcessError(1, "journalctl", output="failed")],
        itertools.repeat(None),
    )
    export_logs.export_container_logs(tmp_path)

    expected_msg = (
        "Failed to export logs for quipucords-app.service. "
        "Exported logs may be incomplete."
    )
    assert expected_msg in caplog.text

    expected_calls = []
    for service in settings.SYSTEMD_SERVICE_FILENAMES:
        expected_calls.append(
            mock.call(
                ["journalctl", f"--user-unit={service}"],
                wait_timeout=mock.ANY,
                bufsize=mock.ANY,
                stdout=mock.ANY,
                stderr=subprocess.STDOUT,
            )
        )
    assert mock_shell_utils.run_command.call_count == len(
        settings.SYSTEMD_SERVICE_FILENAMES
    )
    mock_shell_utils.run_command.assert_has_calls(expected_calls)


def test_copy_qpc_log_happy_path(
    temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Test happy path for copy_qpc_log: file is copied."""
    reference_content = "qpc commands log"
    qpc_dir = (temp_config_directories["SERVER_DATA_DIR"] / "../qpc").resolve()
    qpc_dir.mkdir()
    qpc_log = qpc_dir / "qpc.log"
    qpc_log.write_text(reference_content)

    export_logs.copy_qpc_log(archive_dir)

    assert (archive_dir / "qpc.log").read_text() == reference_content


def test_copy_qpc_log_no_dir(
    caplog, temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Check copy_qpc_log can handle missing directory."""
    caplog.set_level(logging.INFO)
    qpc_log = (temp_config_directories["SERVER_DATA_DIR"] / "../qpc/qpc.log").resolve()

    export_logs.copy_qpc_log(archive_dir)

    expected_msg = f"CLI log directory ({qpc_log.parent.as_posix()}) does not exist"
    last_log = caplog.records[-1]
    assert expected_msg in last_log.message
    assert last_log.levelno == logging.INFO


def test_copy_qpc_log_no_file(
    caplog, temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Check copy_qpc_log can handle missing file."""
    caplog.set_level(logging.INFO)
    qpc_log = (temp_config_directories["SERVER_DATA_DIR"] / "../qpc/qpc.log").resolve()
    qpc_log.parent.mkdir(parents=True)

    export_logs.copy_qpc_log(archive_dir)

    expected_msg = f"CLI log file ({qpc_log.as_posix()}) does not exist"
    last_log = caplog.records[-1]
    assert expected_msg in last_log.message
    assert last_log.levelno == logging.INFO


def test_copy_qpc_log_wrong_permissions(
    caplog, temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Check copy_qpc_log can handle log file with wrong permissions."""
    caplog.set_level(logging.ERROR)
    qpc_dir = (temp_config_directories["SERVER_DATA_DIR"] / "../qpc").resolve()
    qpc_dir.mkdir()
    qpc_log = qpc_dir / "qpc.log"
    qpc_log.touch(mode=0o222)

    export_logs.copy_qpc_log(archive_dir)

    expected_msg = f"Permission denied trying to access {qpc_log.as_posix()}."
    last_log = caplog.records[-1]
    assert expected_msg in last_log.message
    assert last_log.levelno == logging.ERROR


def test_copy_postgres_logs_happy_path(
    temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Test happy path for copy_postgres_logs: files are copied."""
    reference_content = "detailed postgres logs"
    postgres_dir = (
        temp_config_directories["SERVER_DATA_DIR"] / "db/userdata/log/"
    ).resolve()
    postgres_dir.mkdir(parents=True)
    postgres_log = postgres_dir / "postgresql-Mon.log"
    postgres_log.write_text(reference_content)

    export_logs.copy_postgres_logs(archive_dir)

    assert (
        archive_dir / "postgres/postgresql-Mon.log"
    ).read_text() == reference_content


def test_copy_postgres_logs_wrong_permissions(
    caplog, temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Check copy_postgres_logs can handle log file with wrong permissions."""
    caplog.set_level(logging.ERROR)
    postgres_dir = (
        temp_config_directories["SERVER_DATA_DIR"] / "db/userdata/log/"
    ).resolve()
    postgres_dir.mkdir(parents=True)
    postgres_log = postgres_dir / "postgresql-Mon.log"
    postgres_log.touch(mode=0o222)

    export_logs.copy_postgres_logs(archive_dir)

    expected_msg = f"Failed to copy some files from {postgres_dir.as_posix()}."
    assert expected_msg in caplog.text


def test_copy_postgres_logs_no_source(
    temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """
    Check copy_postgres_logs can handle missing postgres directory.

    This test is very implicit. Source (postgres) directory does not exist, as we did
    not create it explicitly. Implementation silently swallows relevant exception, so
    there is not much to assert on.
    """
    export_logs.copy_postgres_logs(archive_dir)
    assert not (archive_dir / "postgres").exists()


def test_copy_nginx_logs_happy_path(
    temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Test happy path for copy_nginx_logs: files are copied."""
    reference_content = "detailed nginx logs"
    nginx_dir = (temp_config_directories["SERVER_DATA_DIR"] / "log/nginx/").resolve()
    nginx_dir.mkdir(parents=True)
    nginx_log = nginx_dir / "access.log"
    nginx_log.write_text(reference_content)

    export_logs.copy_nginx_logs(archive_dir)

    assert (archive_dir / "nginx/access.log").read_text() == reference_content


def test_copy_nginx_logs_wrong_permissions(
    caplog, temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """Check copy_nginx_logs can handle a log file with wrong permissions."""
    caplog.set_level(logging.ERROR)
    nginx_dir = (temp_config_directories["SERVER_DATA_DIR"] / "log/nginx/").resolve()
    nginx_dir.mkdir(parents=True)
    nginx_log = nginx_dir / "access.log"
    nginx_log.touch(mode=0o222)

    export_logs.copy_nginx_logs(archive_dir)

    expected_msg = f"Failed to copy some files from {nginx_dir.as_posix()}."
    assert expected_msg in caplog.text


def test_copy_nginx_logs_no_source(
    temp_config_directories: dict[str, pathlib.Path], archive_dir: pathlib.Path
):
    """
    Check copy_nginx_logs can handle missing postgres directory.

    This test is very implicit. Source (nginx) directory does not exist, as we did
    not create it explicitly. Implementation silently swallows relevant exception, so
    there is not much to assert on.
    """
    export_logs.copy_nginx_logs(archive_dir)
    assert not (archive_dir / "nginx").exists()
