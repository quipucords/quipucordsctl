"""Test the "start" command."""

from unittest import mock

from quipucordsctl import argparse_utils, settings
from quipucordsctl.commands import start


def test_get_help():
    """Test get_help returns an appropriate string."""
    assert settings.SERVER_SOFTWARE_NAME in start.get_help()


def test_get_description():
    """Test get_description returns an appropriate string."""
    assert settings.SERVER_SOFTWARE_NAME in start.get_description()


def test_get_display_group():
    """Test get_display_group returns MAIN."""
    assert start.get_display_group() == argparse_utils.DisplayGroups.MAIN


def test_start_run_happy_path():
    """Test the start command happy path."""
    mock_args = mock.Mock()
    mock_args.quiet = False

    with (
        mock.patch.object(start, "systemctl_utils") as mock_systemctl_utils,
        mock.patch.object(start, "podman_utils") as mock_podman_utils,
    ):
        mock_podman_utils.ensure_images.return_value = True
        mock_systemctl_utils.start_service.return_value = True

        result = start.run(mock_args)

        assert result is True
        mock_systemctl_utils.ensure_systemd_user_session.assert_called_once()
        mock_podman_utils.ensure_podman_socket.assert_called_once()
        mock_podman_utils.ensure_cgroups_v2.assert_called_once()
        mock_podman_utils.ensure_images.assert_called_once()
        mock_systemctl_utils.start_service.assert_called_once()


def test_start_run_fails_when_ensure_images_fails():
    """Test start returns False when ensure_images fails."""
    mock_args = mock.Mock()

    with (
        mock.patch.object(start, "systemctl_utils") as mock_systemctl_utils,
        mock.patch.object(start, "podman_utils") as mock_podman_utils,
    ):
        mock_podman_utils.ensure_images.return_value = False

        result = start.run(mock_args)

        assert result is False
        mock_podman_utils.ensure_images.assert_called_once()
        mock_systemctl_utils.start_service.assert_not_called()


def test_start_run_fails_when_start_service_fails():
    """Test start returns False when start_service fails."""
    mock_args = mock.Mock()
    mock_args.quiet = False

    with (
        mock.patch.object(start, "systemctl_utils") as mock_systemctl_utils,
        mock.patch.object(start, "podman_utils") as mock_podman_utils,
    ):
        mock_podman_utils.ensure_images.return_value = True
        mock_systemctl_utils.start_service.return_value = False

        result = start.run(mock_args)

        assert result is False
        mock_systemctl_utils.start_service.assert_called_once()


def test_start_run_quiet_suppresses_success_message(capsys):
    """Test that --quiet suppresses the success print."""
    mock_args = mock.Mock()
    mock_args.quiet = True

    with (
        mock.patch.object(start, "systemctl_utils") as mock_systemctl_utils,
        mock.patch.object(start, "podman_utils") as mock_podman_utils,
    ):
        mock_podman_utils.ensure_images.return_value = True
        mock_systemctl_utils.start_service.return_value = True

        result = start.run(mock_args)

        assert result is True
        captured = capsys.readouterr()
        assert captured.out == ""


def test_start_run_prints_success_message(capsys):
    """Test that success message is printed when not quiet."""
    mock_args = mock.Mock()
    mock_args.quiet = False

    with (
        mock.patch.object(start, "systemctl_utils") as mock_systemctl_utils,
        mock.patch.object(start, "podman_utils") as mock_podman_utils,
    ):
        mock_podman_utils.ensure_images.return_value = True
        mock_systemctl_utils.start_service.return_value = True

        result = start.run(mock_args)

        assert result is True
        captured = capsys.readouterr()
        assert settings.SERVER_SOFTWARE_NAME in captured.out
