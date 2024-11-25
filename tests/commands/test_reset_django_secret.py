"""Test the "reset_django_secret" command."""

from unittest import mock

# TODO FIXME Implement the rest of these tests.
from quipucordsctl.commands import reset_django_secret


def test_django_secret_is_set():
    """Test placeholder for django_secret_is_set."""
    assert not reset_django_secret.django_secret_is_set()


def test_reset_django_secret_run():
    """Test placeholder for reset_django_secret.run."""
    mock_args = mock.Mock()
    assert reset_django_secret.run(mock_args) is None
