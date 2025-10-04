"""Test the "reset_encryption_secret" command."""

import argparse
import logging
from unittest import mock

import pytest

from quipucordsctl.commands import reset_encryption_secret


@mock.patch.object(reset_encryption_secret.podman_utils, "secret_exists")
def test_encryption_secret_is_set(mock_secret_exists):
    """Test encryption_secret_is_set just wraps secret_exists."""
    assert reset_encryption_secret.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(
        reset_encryption_secret.PODMAN_SECRET_NAME
    )


@pytest.fixture
def first_time_run(mocker):
    """Mock certain behaviors to act like this is a first-time default run."""
    mocker.patch.object(
        reset_encryption_secret.podman_utils, "secret_exists", return_value=False
    )
    mocker.patch.object(
        reset_encryption_secret.secrets.shell_utils, "get_env", return_value=None
    )


def test_reset_encryption_secret_run_success(
    first_time_run, good_secret, mocker, caplog
):
    """Test reset_encryption_secret.run in the default happy path."""
    mocker.patch.object(
        reset_encryption_secret.secrets,
        "generate_random_secret",
        return_value=good_secret,
    )
    mocker.patch.object(
        reset_encryption_secret.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    expected_last_log_messages = [
        "New value for podman secret 'quipucords-encryption-secret-key' "
        "was randomly generated.",
        "The encryption secret key was successfully updated.",
    ]

    assert reset_encryption_secret.run(argparse.Namespace())
    assert expected_last_log_messages == caplog.messages[-2:]


def test_reset_encryption_secret_run_set_secret_failure(
    first_time_run, good_secret, mocker, caplog
):
    """Test reset_encryption_secret.run when set_secret fails unexpectedly."""
    mocker.patch.object(
        reset_encryption_secret.secrets,
        "generate_random_secret",
        return_value=good_secret,
    )
    mocker.patch.object(
        reset_encryption_secret.podman_utils,
        "set_secret",
        return_value=False,  # something broke unexpectedly
    )

    caplog.set_level(logging.ERROR)
    expected_last_log_message = "The encryption secret key was not updated."

    assert not reset_encryption_secret.run(argparse.Namespace())
    assert expected_last_log_message == caplog.messages[0]
