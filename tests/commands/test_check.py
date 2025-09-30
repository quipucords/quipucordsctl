"""Test the "check" command."""

import logging
import os
import pathlib
import stat
from collections.abc import Generator
from typing import Any
from unittest import mock

import pytest

from quipucordsctl import settings
from quipucordsctl.commands import check


@pytest.fixture
def temp_config_directories(
    tmp_path: pathlib.Path, monkeypatch
) -> Generator[dict[str, pathlib.Path], Any, None]:
    """Temporarily swap any directories the "check" command would examine."""
    temp_settings_dirs = {}
    for settings_dir in ("SERVER_DATA_DIR", "SERVER_ENV_DIR", "SYSTEMD_UNITS_DIR"):
        new_path = tmp_path / settings_dir
        monkeypatch.setattr(
            f"quipucordsctl.commands.check.settings.{settings_dir}", new_path
        )
        temp_settings_dirs[settings_dir] = new_path
    
    tmp_data_dirs = {
        data_dir: temp_settings_dirs["SERVER_DATA_DIR"] / data_dir
        for data_dir in ("certs", "data", "db", "log", "sshkeys")
    }
    monkeypatch.setattr(
        "quipucordsctl.commands.check.settings.SERVER_DATA_SUBDIRS", tmp_data_dirs
    )
    yield temp_settings_dirs


def test_check_directory_status_missing(tmp_path: pathlib.Path):
    """Test check_directory_status returns 3 for missing directory."""
    missing_dir = tmp_path / "missing_directory"
    status = check.check_directory_status(missing_dir)
    assert status == 3


def test_check_directory_status_not_directory(tmp_path: pathlib.Path):
    """Test check_directory_status returns 3 when path is a file, not directory."""
    file_path = tmp_path / "is_a_file"
    file_path.touch()
    status = check.check_directory_status(file_path)
    assert status == 3


def test_check_directory_status_ok(tmp_path: pathlib.Path):
    """Test check_directory_status returns 0 for valid directory."""
    valid_dir = tmp_path / "valid_directory"
    valid_dir.mkdir()
    status = check.check_directory_status(valid_dir)
    assert status == 0


def test_check_directory_status_bad_permissions(tmp_path: pathlib.Path):
    """Test check_directory_status returns 1 for directory with bad permissions."""
    bad_perms_dir = tmp_path / "bad_perms_directory"
    bad_perms_dir.mkdir()
    bad_perms_dir.chmod(stat.S_IWUSR | stat.S_IXUSR)
    try:
        status = check.check_directory_status(bad_perms_dir)
        assert status == 1
    finally:
        # Reset permissions so pytest can clean up
        bad_perms_dir.chmod(0o755)


def test_check_file_status_missing(tmp_path: pathlib.Path):
    """Test check_file_status returns 3 for missing file."""
    missing_file = tmp_path / "missing_file.txt"
    status = check.check_file_status(missing_file)
    assert status == 3


def test_check_file_status_not_file(tmp_path: pathlib.Path):
    """Test check_file_status returns 3 when path is a directory, not file."""
    dir_path = tmp_path / "is_a_directory"
    dir_path.mkdir()
    status = check.check_file_status(dir_path)
    assert status == 3


def test_check_file_status_ok(tmp_path: pathlib.Path):
    """Test check_file_status returns 0 for valid file."""
    valid_file = tmp_path / "valid_file.txt"
    valid_file.touch()
    status = check.check_file_status(valid_file)
    assert status == 0


def test_check_file_status_bad_permissions(tmp_path: pathlib.Path):
    """Test check_file_status returns 1 for file with bad permissions."""
    bad_perms_file = tmp_path / "bad_perms_file.txt"
    bad_perms_file.touch()
    bad_perms_file.chmod(stat.S_IWUSR)
    try:
        status = check.check_file_status(bad_perms_file)
        assert status == 1
    finally:
        # Reset permissions for cleanup
        bad_perms_file.chmod(0o644)


def test_print_path_status_ok(caplog, tmp_path: pathlib.Path):
    """Test print_path_status with status 0 (OK)."""
    caplog.set_level(logging.INFO)
    test_path = tmp_path / "test_path"
    test_path.touch()
    
    check.print_path_status(0, test_path)
    
    assert len(caplog.messages) == 1
    assert "OK" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_print_path_status_missing(caplog, tmp_path: pathlib.Path):
    """Test print_path_status with status 3 (Missing)."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "missing_path"
    
    check.print_path_status(3, test_path)
    
    assert len(caplog.messages) == 1
    assert "ERROR: Missing" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_print_path_status_bad_permissions(caplog, tmp_path: pathlib.Path):
    """Test print_path_status with status 1 (Bad permissions)."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "bad_perms_path"
    test_path.touch()
    test_path.chmod(stat.S_IWUSR)
    try:
        check.print_path_status(1, test_path)
        assert len(caplog.messages) == 1
        assert "ERROR: Incorrect permission(s)" in caplog.messages[0]
        assert str(test_path) in caplog.messages[0]
    finally:
        test_path.chmod(0o644)

def test_print_path_status_not_owned(caplog, tmp_path: pathlib.Path):
    """Test print_path_status with status 2 (Not owned by user)."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "not_owned_path"
    test_path.touch()
    
    check.print_path_status(2, test_path)
    
    assert len(caplog.messages) == 1
    assert "ERROR: Not owned by you" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def test_print_path_status_unknown(caplog, tmp_path: pathlib.Path):
    """Test print_path_status with unknown status."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "test_path"
    
    check.print_path_status(99, test_path)
    
    assert len(caplog.messages) == 1
    assert "ERROR: Unknown status" in caplog.messages[0]
    assert str(test_path) in caplog.messages[0]


def create_full_quipucords_structure(temp_dirs: dict[str, pathlib.Path]) -> None:
    """Helper function to create a complete, valid Quipucords directory structure."""
    for dir_path in temp_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    for subdir_name in ("certs", "data", "db", "log", "sshkeys"):
        subdir_path = temp_dirs["SERVER_DATA_DIR"] / subdir_name
        subdir_path.mkdir(parents=True, exist_ok=True)
    
    (temp_dirs["SERVER_DATA_DIR"] / "certs" / "server.key").touch()
    (temp_dirs["SERVER_DATA_DIR"] / "certs" / "server.crt").touch()
    (temp_dirs["SERVER_DATA_DIR"] / "data" / "secret.txt").touch()
    
    (temp_dirs["SERVER_DATA_DIR"] / "db" / "userdata").mkdir(parents=True, exist_ok=True)
    
    for env_filename in settings.TEMPLATE_SERVER_ENV_FILENAMES:
        (temp_dirs["SERVER_ENV_DIR"] / env_filename).touch()
    
    for unit_filename in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        (temp_dirs["SYSTEMD_UNITS_DIR"] / unit_filename).touch()


def test_run_all_files_missing(temp_config_directories: dict[str, pathlib.Path], caplog):
    """Test run when all files and directories are missing."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()
    
    
    with pytest.raises(SystemExit) as exc_info:
        check.run(mock_args)
    
    expected_error_count = 24
    assert exc_info.value.code == expected_error_count
    
    error_messages = [msg for msg in caplog.messages if "Found" in msg and "issues" in msg]
    assert len(error_messages) == 1
    assert f"Found {expected_error_count} issues" in error_messages[0]


def test_run_all_files_present_and_valid(temp_config_directories: dict[str, pathlib.Path], caplog):
    """Test run when all files and directories are present and valid."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()
    
    create_full_quipucords_structure(temp_config_directories)
    
    result = check.run(mock_args)
    
    assert result is True
    
    success_messages = [msg for msg in caplog.messages if "All checks passed successfully" in msg]
    assert len(success_messages) == 1


def test_run_some_files_missing(temp_config_directories: dict[str, pathlib.Path], caplog):
    """Test run when some files are missing."""
    caplog.set_level(logging.INFO)
    mock_args = mock.Mock()
    
    temp_config_directories["SERVER_DATA_DIR"].mkdir(parents=True, exist_ok=True)
    (temp_config_directories["SERVER_DATA_DIR"] / "certs").mkdir(parents=True, exist_ok=True)
    
    with pytest.raises(SystemExit) as exc_info:
        check.run(mock_args)
    
    assert exc_info.value.code > 0
    
    error_messages = [msg for msg in caplog.messages if "ERROR: Missing" in msg]
    assert len(error_messages) > 0


def test_run_permission_issues(temp_config_directories: dict[str, pathlib.Path], caplog):
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

        permission_errors = [msg for msg in caplog.messages if "Incorrect permission" in msg]
        assert len(permission_errors) > 0
    finally:
        # Reset permissions to allow pytest cleanup
        server_key.chmod(0o644)


def test_check_directory_and_print_status_returns_correct_status(tmp_path: pathlib.Path):
    """Test that check_directory_and_print_status returns the status from check_directory_status."""
    missing_dir = tmp_path / "missing"
    
    with mock.patch.object(check, 'print_path_status') as mock_print:
        status = check.check_directory_and_print_status(missing_dir)
        
        assert status == 3  # Missing
        mock_print.assert_called_once_with(3, missing_dir)


def test_check_file_and_print_status_returns_correct_status(tmp_path: pathlib.Path):
    """Test that check_file_and_print_status returns the status from check_file_status."""
    missing_file = tmp_path / "missing.txt"
    
    with mock.patch.object(check, 'print_path_status') as mock_print:
        status = check.check_file_and_print_status(missing_file)
        
        assert status == 3
        mock_print.assert_called_once_with(3, missing_file)


def test_get_help():
    """Test that get_help returns expected help text."""
    help_text = check.get_help()
    assert "Check that all necessary files and directories exist" in help_text
    assert settings.SERVER_SOFTWARE_NAME in help_text


def test_check_directory_status_with_permission_error(tmp_path: pathlib.Path):
    """Test check_directory_status when stat() raises PermissionError."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    
    with mock.patch.object(pathlib.Path, 'stat', side_effect=PermissionError):
        status = check.check_directory_status(test_dir)
        assert status == 1


def test_check_file_status_with_permission_error(tmp_path: pathlib.Path):
    """Test check_file_status when stat() raises PermissionError."""
    test_file = tmp_path / "test_file.txt"
    test_file.touch()
    
    with mock.patch.object(pathlib.Path, 'stat', side_effect=PermissionError):
        status = check.check_file_status(test_file)
        assert status == 1


def test_print_path_status_handles_stat_errors_gracefully(caplog, tmp_path: pathlib.Path):
    """Test that print_path_status handles stat() errors gracefully."""
    caplog.set_level(logging.ERROR)
    test_path = tmp_path / "test_path"
    test_path.touch()
    

    with mock.patch.object(pathlib.Path, 'stat', side_effect=OSError):
        check.print_path_status(1, test_path)
    
    assert len(caplog.messages) == 1
    assert "ERROR: Incorrect permissions" in caplog.messages[0]


@pytest.mark.parametrize("owner_method_error", [OSError, KeyError])
def test_print_path_status_handles_owner_errors(owner_method_error, caplog, tmp_path: pathlib.Path):
    """Test that print_path_status handles Path.owner() errors gracefully."""
    caplog.set_level(logging.INFO)
    test_path = tmp_path / "test_path"
    test_path.touch()
    
    with mock.patch.object(pathlib.Path, 'owner', side_effect=owner_method_error):
        check.print_path_status(0, test_path)
    
    assert len(caplog.messages) == 1
    assert "OK" in caplog.messages[0]

