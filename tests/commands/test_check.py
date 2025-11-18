"""Test the "check" command."""

import logging
import pathlib
import stat
from unittest import mock

import pytest

from quipucordsctl import settings
from quipucordsctl.commands import check
from quipucordsctl.commands.check import PathCheckResult, StatusType


@pytest.mark.parametrize(
    "missing_ok,expected_status",
    (
        (False, StatusType.MISSING),
        (True, StatusType.OK_MISSING),
    ),
)
def test_check_directory_status_missing(
    tmp_path: pathlib.Path, missing_ok, expected_status
):
    """Test check_directory_status returns MISSING for missing directory."""
    missing_dir = tmp_path / "missing_directory"
    result = check.check_directory_status(missing_dir, missing_ok=missing_ok)
    assert result.status == expected_status
    assert result.path == missing_dir
    assert result.stat_info is None


def test_check_directory_status_not_directory(tmp_path: pathlib.Path):
    """Test check_directory_status returns MISSING when path is file, not directory."""
    file_path = tmp_path / "is_a_file"
    file_path.touch()
    result = check.check_directory_status(file_path)
    assert result.status == StatusType.MISSING
    assert result.path == file_path
    assert result.stat_info is None


def test_check_directory_status_ok(tmp_path: pathlib.Path):
    """Test check_directory_status returns OK for valid directory."""
    valid_dir = tmp_path / "valid_directory"
    valid_dir.mkdir()
    result = check.check_directory_status(valid_dir)
    assert result.status == StatusType.OK
    assert result.path == valid_dir
    assert result.stat_info is not None


def test_check_directory_status_bad_permissions(tmp_path: pathlib.Path):
    """Test check_directory_status returns BAD_PERMISSIONS for directory."""
    bad_perms_dir = tmp_path / "bad_perms_directory"
    bad_perms_dir.mkdir()
    bad_perms_dir.chmod(stat.S_IWUSR | stat.S_IXUSR)
    try:
        result = check.check_directory_status(bad_perms_dir)
        assert result.status == StatusType.BAD_PERMISSIONS
        assert result.path == bad_perms_dir
        assert result.stat_info is not None
    finally:
        # Reset permissions so pytest can clean up
        bad_perms_dir.chmod(0o755)


@pytest.mark.parametrize(
    "missing_ok,expected_status",
    (
        (False, StatusType.MISSING),
        (True, StatusType.OK_MISSING),
    ),
)
def test_check_file_status_missing(tmp_path: pathlib.Path, missing_ok, expected_status):
    """Test check_file_status returns MISSING for missing file."""
    missing_file = tmp_path / "missing_file.txt"
    result = check.check_file_status(missing_file, missing_ok=missing_ok)
    assert result.status == expected_status
    assert result.path == missing_file
    assert result.stat_info is None


def test_check_file_status_not_file(tmp_path: pathlib.Path):
    """Test check_file_status returns MISSING when path is a directory, not file."""
    dir_path = tmp_path / "is_a_directory"
    dir_path.mkdir()
    result = check.check_file_status(dir_path)
    assert result.status == StatusType.MISSING
    assert result.path == dir_path
    assert result.stat_info is None


def test_check_file_status_ok(tmp_path: pathlib.Path):
    """Test check_file_status returns OK for valid file."""
    valid_file = tmp_path / "valid_file.txt"
    valid_file.touch()
    result = check.check_file_status(valid_file)
    assert result.status == StatusType.OK
    assert result.path == valid_file
    assert result.stat_info is not None


def test_check_file_status_bad_permissions(tmp_path: pathlib.Path):
    """Test check_file_status returns BAD_PERMISSIONS for file with bad permissions."""
    bad_perms_file = tmp_path / "bad_perms_file.txt"
    bad_perms_file.touch()
    bad_perms_file.chmod(stat.S_IWUSR)
    try:
        result = check.check_file_status(bad_perms_file)
        assert result.status == StatusType.BAD_PERMISSIONS
        assert result.path == bad_perms_file
        assert result.stat_info is not None
    finally:
        # Reset permissions for cleanup
        bad_perms_file.chmod(0o644)


def test_log_path_status_ok(caplog, tmp_path: pathlib.Path):
    """Test log_path_status with OK status."""
    caplog.set_level(logging.INFO)
    test_path = tmp_path / "test_path"
    test_path.touch()

    result = PathCheckResult(StatusType.OK, test_path, test_path.stat())
    check.log_path_status(result)

    assert len(caplog.messages) == 1
    assert "OK" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_log_path_status_missing(caplog, tmp_path: pathlib.Path):
    """Test log_path_status with MISSING status."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "missing_path"

    result = PathCheckResult(StatusType.MISSING, test_path)
    check.log_path_status(result)

    assert len(caplog.messages) == 1
    assert "ERROR: Missing" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_log_path_status_ok_missing(caplog, tmp_path: pathlib.Path):
    """Test log_path_status with OK_MISSING status."""
    caplog.set_level(logging.INFO)
    test_path = tmp_path / "missing_path"

    result = PathCheckResult(StatusType.OK_MISSING, test_path)
    check.log_path_status(result)

    assert len(caplog.messages) == 1
    assert "Missing, will be created during server startup" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_log_path_status_bad_permissions(caplog, tmp_path: pathlib.Path):
    """Test log_path_status with BAD_PERMISSIONS status."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "bad_perms_path"
    test_path.touch()
    test_path.chmod(stat.S_IWUSR)
    try:
        result = PathCheckResult(
            StatusType.BAD_PERMISSIONS, test_path, test_path.stat()
        )
        check.log_path_status(result)
        assert len(caplog.messages) == 1
        assert "ERROR: Incorrect permission(s)" in caplog.messages[0]
        assert str(test_path) in caplog.messages[0]
    finally:
        test_path.chmod(0o644)


def test_log_path_status_not_owned(caplog, tmp_path: pathlib.Path):
    """Test log_path_status with WRONG_OWNER status."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "not_owned_path"
    test_path.touch()

    result = PathCheckResult(StatusType.WRONG_OWNER, test_path, test_path.stat())
    check.log_path_status(result)

    assert len(caplog.messages) == 1
    assert "ERROR: Not owned by you" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_log_path_status_unknown(caplog, tmp_path: pathlib.Path):
    """Test log_path_status with unknown status (should not happen in practice)."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "test_path"

    # Create a mock status that's not one of our enum values
    class MockStatus:
        pass

    result = PathCheckResult(MockStatus(), test_path)
    check.log_path_status(result)

    assert len(caplog.messages) == 1
    assert "ERROR: Unknown status" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def create_full_quipucords_structure(temp_dirs: dict[str, pathlib.Path]) -> None:
    """Create a complete, valid Quipucords directory structure."""
    for dir_path in temp_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    for subdir_name in ("certs", "data", "db", "log", "sshkeys"):
        subdir_path = temp_dirs["SERVER_DATA_DIR"] / subdir_name
        subdir_path.mkdir(parents=True, exist_ok=True)

    (temp_dirs["SERVER_DATA_DIR"] / "certs" / "server.key").touch()
    (temp_dirs["SERVER_DATA_DIR"] / "certs" / "server.crt").touch()

    (temp_dirs["SERVER_DATA_DIR"] / "db" / "userdata").mkdir(
        parents=True, exist_ok=True
    )

    for env_filename in settings.TEMPLATE_SERVER_ENV_FILENAMES:
        (temp_dirs["SERVER_ENV_DIR"] / env_filename).touch()

    for unit_filename in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        (temp_dirs["SYSTEMD_UNITS_DIR"] / unit_filename).touch()


@mock.patch.object(check, "check_service_running")
def test_run_all_files_missing(
    mock_check_running, temp_config_directories: dict[str, pathlib.Path], caplog
):
    """Test run when all files and directories are missing."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()
    mock_check_running.side_effect = [True]

    with pytest.raises(SystemExit) as exc_info:
        check.run(mock_args)

    expected_error_count = 23
    assert exc_info.value.code == expected_error_count

    error_messages = [
        msg for msg in caplog.messages if "Found" in msg and "issues" in msg
    ]
    assert len(error_messages) == 1
    assert f"Found {expected_error_count} issues" in error_messages[0]


def test_run_all_files_present_and_valid(
    temp_config_directories: dict[str, pathlib.Path], caplog
):
    """Test run when all files and directories are present and valid."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()

    create_full_quipucords_structure(temp_config_directories)

    result = check.run(mock_args)

    assert result is True

    success_messages = [
        msg for msg in caplog.messages if "All checks passed successfully" in msg
    ]
    assert len(success_messages) == 1


def test_run_some_files_missing(
    temp_config_directories: dict[str, pathlib.Path], caplog
):
    """Test run when some files are missing."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()

    temp_config_directories["SERVER_DATA_DIR"].mkdir(parents=True, exist_ok=True)
    (temp_config_directories["SERVER_DATA_DIR"] / "certs").mkdir(
        parents=True, exist_ok=True
    )

    with pytest.raises(SystemExit) as exc_info:
        check.run(mock_args)

    assert exc_info.value.code > 0

    error_messages = [msg for msg in caplog.messages if "ERROR: Missing" in msg]
    assert len(error_messages) > 0


def test_run_permission_issues(
    temp_config_directories: dict[str, pathlib.Path], caplog
):
    """Test run when files exist but have permission issues."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()

    create_full_quipucords_structure(temp_config_directories)

    server_key = temp_config_directories["SERVER_DATA_DIR"] / "certs" / "server.key"
    server_key.chmod(0o000)  # No permissions at all

    try:
        with pytest.raises(SystemExit) as exc_info:
            check.run(mock_args)
        assert exc_info.value.code > 0

        permission_errors = [
            msg for msg in caplog.messages if "Incorrect permission" in msg
        ]
        assert len(permission_errors) > 0
    finally:
        # Reset permissions to allow pytest cleanup
        server_key.chmod(0o644)


@pytest.mark.parametrize(
    "missing_ok,expected_status",
    (
        (False, StatusType.MISSING),
        (True, StatusType.OK_MISSING),
    ),
)
def test_check_directory_and_print_status_returns_correct_status(
    tmp_path: pathlib.Path, missing_ok, expected_status
):
    """Test that check_directory_and_print_status returns False for missing dir."""
    missing_dir = tmp_path / "missing"

    with mock.patch.object(check, "log_path_status") as mock_log:
        result = check.check_directory_and_print_status(
            missing_dir, missing_ok=missing_ok
        )

        assert result is missing_ok  # Missing directory should return False
        mock_log.assert_called_once()
        # Verify the PathCheckResult passed to log_path_status
        call_args = mock_log.call_args[0][0]
        assert call_args.status == expected_status
        assert call_args.path == missing_dir


@pytest.mark.parametrize(
    "missing_ok,expected_status",
    (
        (False, StatusType.MISSING),
        (True, StatusType.OK_MISSING),
    ),
)
def test_check_file_and_print_status_returns_correct_status(
    tmp_path: pathlib.Path, missing_ok, expected_status
):
    """Test that check_file_and_print_status returns False for missing file."""
    missing_file = tmp_path / "missing.txt"

    with mock.patch.object(check, "log_path_status") as mock_log:
        result = check.check_file_and_print_status(missing_file, missing_ok=missing_ok)

        assert result is missing_ok  # Missing file should return False
        mock_log.assert_called_once()
        # Verify the PathCheckResult passed to log_path_status
        call_args = mock_log.call_args[0][0]
        assert call_args.status == expected_status
        assert call_args.path == missing_file


def test_get_help():
    """Test that get_help returns expected help text."""
    help_text = check.get_help()
    assert "Check that all necessary files and directories exist" in help_text
    assert settings.SERVER_SOFTWARE_NAME in help_text


def test_check_directory_status_with_permission_error(tmp_path: pathlib.Path):
    """Test check_directory_status when stat() raises PermissionError."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    with mock.patch.object(pathlib.Path, "stat", side_effect=PermissionError):
        result = check.check_directory_status(test_dir)
        assert result.status == StatusType.BAD_PERMISSIONS
        assert result.path == test_dir
        assert result.stat_info is None


def test_check_file_status_with_permission_error(tmp_path: pathlib.Path):
    """Test check_file_status when stat() raises PermissionError."""
    test_file = tmp_path / "test_file.txt"
    test_file.touch()

    with mock.patch.object(pathlib.Path, "stat", side_effect=PermissionError):
        result = check.check_file_status(test_file)
        assert result.status == StatusType.BAD_PERMISSIONS
        assert result.path == test_file
        assert result.stat_info is None


def test_log_path_status_handles_stat_errors_gracefully(caplog, tmp_path: pathlib.Path):
    """Test that log_path_status handles stat() errors gracefully."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "test_path"
    test_path.touch()

    # Create result with stat_info=None to simulate error during stat capture
    result = PathCheckResult(StatusType.BAD_PERMISSIONS, test_path, None)
    check.log_path_status(result)

    assert len(caplog.messages) == 1
    assert "ERROR: Incorrect permissions" in caplog.messages[0]


@pytest.mark.parametrize("owner_method_error", [OSError, KeyError])
def test_log_path_status_handles_owner_errors(
    owner_method_error, caplog, tmp_path: pathlib.Path
):
    """Test that log_path_status handles Path.owner() errors gracefully."""
    caplog.set_level(logging.INFO)
    test_path = tmp_path / "test_path"
    test_path.touch()

    result = PathCheckResult(StatusType.OK, test_path, test_path.stat())
    with mock.patch.object(pathlib.Path, "owner", side_effect=owner_method_error):
        check.log_path_status(result)

    assert len(caplog.messages) == 2
    assert "Unexpected error reporting status" in caplog.messages[0]
    assert "OK" in caplog.messages[1]
