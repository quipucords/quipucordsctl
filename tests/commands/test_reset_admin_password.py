"""Test the "reset_admin_password" command."""

from unittest import mock

# TODO FIXME Implement the rest of these tests.
from quipucordsctl.commands import reset_admin_password


def test_server_password_is_set():
    """Test placeholder for django_secret_is_set."""
    assert not reset_admin_password.server_password_is_set()


def test_reset_django_secret_run():
    """Test placeholder for reset_admin_password.run."""
    mock_args = mock.Mock()
    assert reset_admin_password.run(mock_args) is None
