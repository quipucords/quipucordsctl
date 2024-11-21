"""Test the "reset_server_password" command."""
# TODO FIXME Implement the rest of these tests.

from quipucordsctl.commands import reset_server_password


def test_server_password_is_set():
    """Test placeholder for django_secret_is_set."""
    assert not reset_server_password.server_password_is_set()


def test_reset_django_secret_run():
    """Test placeholder for reset_server_password.run."""
    assert reset_server_password.run() is None
