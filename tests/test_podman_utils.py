"""Test the quipucordsctl.podman_utils module."""

import logging
from unittest import mock

import pytest
from podman import errors as podman_errors

from quipucordsctl import podman_utils


@mock.patch.object(podman_utils, "get_podman_client")
def test_secret_exists(mock_get_podman_client, faker):
    """Test the secret_exists function is a simple facade over the podman client."""
    secret_name = faker.slug()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.side_effect = [True, False, True]

    assert podman_utils.secret_exists(secret_name)
    assert not podman_utils.secret_exists(secret_name)
    assert podman_utils.secret_exists(secret_name)


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret(mock_get_podman_client, good_secret, faker, caplog):
    """Test the set_secret function sets a new secret."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = False

    assert podman_utils.set_secret(secret_name, good_secret)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_not_called()
    mock_podman_client.secrets.create.assert_called_once_with(secret_name, good_secret)
    assert f"New podman secret {secret_name} was set." == caplog.messages[0]


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret_exists_ans_yes_replace(mock_get_podman_client, faker, caplog):
    """Test the set_secret function replaces existing secret."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True

    assert podman_utils.set_secret(secret_name, secret_value)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_called_once_with(secret_name)
    mock_podman_client.secrets.create.assert_called_once_with(secret_name, secret_value)
    assert f"A podman secret {secret_name} already exists." == caplog.messages[0]
    assert f"Old podman secret {secret_name} was removed." == caplog.messages[1]
    assert f"New podman secret {secret_name} was set." == caplog.messages[2]


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret_exists_but_no_replace(mock_get_podman_client, faker, caplog):
    """Test the set_secret function fails if secret exists but not told to replace."""
    caplog.set_level(logging.ERROR)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True

    assert not podman_utils.set_secret(secret_name, secret_value, False)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_not_called()
    mock_podman_client.secrets.create.assert_not_called()
    assert f"A podman secret {secret_name} already exists." == caplog.messages[0]


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret_unhandled_exception(mock_get_podman_client, faker, caplog):
    """
    Test the set_secret function lets exceptions raise up to caller.

    This is okay because we expect main.main to handle all exceptions and exit cleanly.
    """
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True
    mock_podman_client.secrets.remove.side_effect = podman_errors.PodmanError

    with pytest.raises(podman_errors.PodmanError):
        podman_utils.set_secret(secret_name, secret_value)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_called_once_with(secret_name)
    mock_podman_client.secrets.create.assert_not_called()
    assert f"A podman secret {secret_name} already exists." == caplog.messages[0]
    assert len(caplog.messages) == 1
