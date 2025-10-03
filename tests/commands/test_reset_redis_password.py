"""Test the "reset_redis_password" command."""

import argparse
import logging
from unittest import mock

import pytest

from quipucordsctl.commands import reset_redis_password


@mock.patch.object(reset_redis_password.podman_utils, "secret_exists")
def test_redis_password_is_set(mock_secret_exists):
    """Test redis_password_is_set just wraps secret_exists."""
    assert reset_redis_password.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(reset_redis_password.PODMAN_SECRET_NAME)


@pytest.fixture
def first_time_run(mocker):
    """Mock certain behaviors to act like this is a first-time default run."""
    mocker.patch.object(
        reset_redis_password.podman_utils, "secret_exists", return_value=False
    )
    mocker.patch.object(
        reset_redis_password.secrets.shell_utils, "get_env", return_value=None
    )


def test_reset_redis_password_run_success(first_time_run, good_secret, mocker, caplog):
    """Test reset_redis_password.run in the default happy path."""
    mocker.patch.object(
        reset_redis_password.secrets,
        "generate_random_secret",
        return_value=good_secret,
    )
    mocker.patch.object(
        reset_redis_password.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    expected_last_log_messages = [
        "New value for podman secret 'quipucords-redis-password' "
        "was randomly generated.",
        "The Redis password was successfully updated.",
    ]

    assert reset_redis_password.run(argparse.Namespace())
    assert expected_last_log_messages == caplog.messages[-2:]


def test_reset_redis_password_run_uses_env_var(good_secret, mocker, caplog):
    """Test reset_redis_password.run uses its environment variable.."""
    mocker.patch.object(
        reset_redis_password.podman_utils,
        "secret_exists",
        return_value=False,
    )
    mocker.patch.object(
        reset_redis_password.secrets.shell_utils,
        "get_env",
        return_value=good_secret,
    )

    set_secret = mocker.patch.object(
        reset_redis_password.podman_utils, "set_secret", return_value=True
    )

    # required b/c non-random values are discouraged
    secrets_runtime = mocker.patch.object(
        reset_redis_password.secrets.settings, "runtime"
    )
    shell_utils_runtime = mocker.patch.object(
        reset_redis_password.secrets.shell_utils.settings, "runtime"
    )
    secrets_runtime.yes = shell_utils_runtime.yes = True

    assert reset_redis_password.run(argparse.Namespace())
    set_secret.assert_called_once_with(
        reset_redis_password.PODMAN_SECRET_NAME, good_secret, False
    )


def test_reset_redis_password_run_set_secret_failure(
    first_time_run, good_secret, mocker, caplog
):
    """Test reset_redis_password.run when set_secret fails unexpectedly."""
    mocker.patch.object(
        reset_redis_password.secrets,
        "generate_random_secret",
        return_value=good_secret,
    )
    mocker.patch.object(
        reset_redis_password.podman_utils,
        "set_secret",
        return_value=False,  # something broke unexpectedly
    )

    caplog.set_level(logging.ERROR)
    expected_last_log_message = "The Redis password was not updated."

    assert not reset_redis_password.run(argparse.Namespace())
    assert expected_last_log_message == caplog.messages[0]
