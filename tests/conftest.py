"""Shared fixtures for pytest tests."""

import importlib
import pathlib
import pkgutil
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def forbid_shell_utils_subprocess(monkeypatch):
    """Forbid subprocess.Popen invocation in tests."""
    mock_subprocess = MagicMock()
    monkeypatch.setattr("quipucordsctl.shell_utils.subprocess.Popen", mock_subprocess)
    mock_subprocess.side_effect = Exception("This should never be called in a test!!!")


@pytest.fixture
def temp_config_directories(
    tmp_path: pathlib.Path, monkeypatch
) -> Generator[dict[str, pathlib.Path], Any, None]:
    """Temporarily swap config directories for ALL commands that need them."""
    temp_settings_dirs = {}

    # Create temp directories
    for settings_dir in ("SERVER_DATA_DIR", "SERVER_ENV_DIR", "SYSTEMD_UNITS_DIR"):
        new_path = tmp_path / settings_dir
        temp_settings_dirs[settings_dir] = new_path

    commands_package = importlib.import_module("quipucordsctl.commands")
    command_names = [
        module_info.name
        for module_info in pkgutil.iter_modules(commands_package.__path__)
    ]
    for command in command_names:
        for settings_dir in ("SERVER_DATA_DIR", "SERVER_ENV_DIR", "SYSTEMD_UNITS_DIR"):
            monkeypatch.setattr(
                f"quipucordsctl.commands.{command}.settings.{settings_dir}",
                temp_settings_dirs[settings_dir],
            )

    # Handle SERVER_DATA_SUBDIRS (include 'certs' for maximum compatibility)
    tmp_data_dirs = {
        data_dir: temp_settings_dirs["SERVER_DATA_DIR"] / data_dir
        for data_dir in ("certs", "data", "db", "log", "sshkeys")  # Include all
    }

    for command in command_names:
        monkeypatch.setattr(
            f"quipucordsctl.commands.{command}.settings.SERVER_DATA_SUBDIRS",
            tmp_data_dirs,
        )

    yield temp_settings_dirs


@pytest.fixture
def good_secret(faker):
    """Generate a "good" secret that should pass validation."""
    return faker.password(
        length=128,  # long enough for all intents and purposes
        special_chars=True,
        digits=True,
        upper_case=True,
        lower_case=True,
    )


@pytest.fixture
def bad_secret(faker):
    """Generate a "bad" secret that should fail validation."""
    return faker.password(
        length=4,  # definitely too short
        special_chars=True,
        digits=False,  # should have a number
        upper_case=False,  # should have a letter
        lower_case=False,  # should have a letter
    )


@pytest.fixture
def mock_first_time_run(mocker):
    """Mock behaviors for a first-time run (secret doesn't exist, no env var)."""

    def _mock_for_module(reset_module):
        mocker.patch.object(
            reset_module.podman_utils,
            "secret_exists",
            return_value=False,
        )
        mocker.patch.object(
            reset_module.secrets.shell_utils,
            "get_env",
            return_value=None,
        )

    return _mock_for_module


def assert_reset_command_help(reset_module, expected_keyword):
    """Assert that reset command has appropriate help text."""
    assert expected_keyword in reset_module.get_help()
    assert f"`{reset_module.__name__.split('.')[-1]}`" in reset_module.get_description()
