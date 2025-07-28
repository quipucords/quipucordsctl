"""Test the "reset_application_secret" command."""

from unittest import mock

from quipucordsctl.commands import reset_application_secret

# TODO FIXME Implement the rest of these tests.


def test_application_secret_is_set():
    """Test placeholder for application_secret_is_set."""
    assert not reset_application_secret.application_secret_is_set()


def test_reset_application_secret_run():
    """Test placeholder for reset_application_secret.run."""
    mock_args = mock.Mock()
    assert reset_application_secret.run(mock_args) is None
