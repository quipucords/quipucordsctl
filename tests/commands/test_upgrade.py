"""Test the "upgrade" command."""

import argparse
import logging
from unittest import mock

import pytest

from quipucordsctl import settings
from quipucordsctl.commands import upgrade


def test_get_help():
    """Test the get_help returns an appropriate string."""
    assert "Upgrade" in upgrade.get_help()


def test_get_description():
    """Test the get_description returns an appropriate string."""
    assert "`upgrade` command" in upgrade.get_description()


@pytest.mark.parametrize(
    "args,attr_name,expected",
    (
        (["--no-pull"], "no_pull", True),
        (["-P"], "no_pull", True),
        ([], "no_pull", False),
        (["--timeout", "1701"], "timeout", 1701),
        (["-t", "1701"], "timeout", 1701),
        ([], "timeout", settings.DEFAULT_PODMAN_PULL_TIMEOUT),
    ),
)
def test_setup_parser(args, attr_name, expected):
    """Test the setup_parser configures parser as expected."""
    parser = argparse.ArgumentParser()
    upgrade.setup_parser(parser)

    value = getattr(parser.parse_args(args), attr_name)
    if type(expected) is bool:
        assert value is expected
    else:
        assert value == expected


@mock.patch("quipucordsctl.commands.upgrade.podman_utils")
def test_pull_latest_images(mock_podman_utils, faker):
    """Test the pull_latest_images function."""
    images = [faker.slug() for _ in range(5)]
    mock_podman_utils.list_expected_podman_container_images.return_value = images
    mock_podman_utils.pull_image.side_effect = [True for _ in images]
    assert upgrade.pull_latest_images()


def test_print_success(capsys):
    """Test that print_success prints the success message."""
    upgrade.print_success()
    captured = capsys.readouterr()
    assert "Upgrade completed successfully." in captured.out
    assert settings.SERVER_SOFTWARE_NAME in captured.out
    assert (
        f"systemctl --user restart {settings.SERVER_SOFTWARE_PACKAGE}-app"
        in captured.out
    )
    assert captured.err == ""


@mock.patch("quipucordsctl.commands.upgrade.pull_latest_images")
@mock.patch("quipucordsctl.commands.upgrade.install.run")
@mock.patch("quipucordsctl.commands.upgrade.systemctl_utils.stop_service")
def test_run_happy_path(
    mock_stop_service, mock_install_run, mock_pull_latest_images, caplog
):
    """Test the upgrade.run happy path."""
    caplog.set_level(logging.WARNING)
    mock_stop_service.return_value = True
    mock_install_run.return_value = True
    mock_pull_latest_images.return_value = True
    mock_args = argparse.Namespace()
    mock_args.no_pull = False
    mock_args.timeout = 0
    mock_args.quiet = False
    assert upgrade.run(mock_args)
    assert caplog.record_tuples == []


@mock.patch("quipucordsctl.commands.upgrade.pull_latest_images")
@mock.patch("quipucordsctl.commands.upgrade.install.run")
@mock.patch("quipucordsctl.commands.upgrade.systemctl_utils.stop_service")
def test_run_happy_path_no_pull(
    mock_stop_service, mock_install_run, mock_pull_latest_images, caplog
):
    """Test the upgrade.run happy path when "no pull" argument is set."""
    caplog.set_level(logging.WARNING)
    mock_stop_service.return_value = True
    mock_install_run.return_value = True
    mock_args = argparse.Namespace()
    mock_args.no_pull = True
    mock_args.timeout = 0
    mock_args.quiet = False
    assert upgrade.run(mock_args)
    mock_pull_latest_images.assert_not_called()
    assert "without pulling" in caplog.messages[-1]


@mock.patch("quipucordsctl.commands.upgrade.pull_latest_images")
@mock.patch("quipucordsctl.commands.upgrade.install.run")
@mock.patch("quipucordsctl.commands.upgrade.systemctl_utils.stop_service")
def test_run_service_stop_fails(
    mock_stop_service, mock_install_run, mock_pull_latest_images, caplog
):
    """Test upgrade.run early return when "stop" fails."""
    caplog.set_level(logging.WARNING)
    mock_stop_service.return_value = False
    mock_args = argparse.Namespace()
    mock_args.no_pull = False
    mock_args.timeout = 0
    mock_args.quiet = False
    assert not upgrade.run(mock_args)
    mock_install_run.assert_not_called()
    mock_pull_latest_images.assert_not_called()


@mock.patch("quipucordsctl.commands.upgrade.pull_latest_images")
@mock.patch("quipucordsctl.commands.upgrade.install.run")
@mock.patch("quipucordsctl.commands.upgrade.systemctl_utils.stop_service")
def test_run_install_fails(
    mock_stop_service, mock_install_run, mock_pull_latest_images, caplog
):
    """Test upgrade.run early return when "install" fails."""
    caplog.set_level(logging.ERROR)
    mock_stop_service.return_value = True
    mock_install_run.return_value = False
    mock_args = argparse.Namespace()
    mock_args.no_pull = False
    mock_args.timeout = 0
    mock_args.quiet = False
    assert not upgrade.run(mock_args)
    mock_pull_latest_images.assert_not_called()
    assert "failed to install normally" in caplog.messages[-1]


@mock.patch("quipucordsctl.commands.upgrade.podman_utils")
@mock.patch("quipucordsctl.commands.upgrade.install.run")
@mock.patch("quipucordsctl.commands.upgrade.systemctl_utils.stop_service")
def test_run_podman_pull_fails(
    mock_stop_service,
    mock_install_run,
    mock_podman_utils,
    caplog,
    faker,
):
    """Test upgrade.run early return when "podman pull" fails."""
    caplog.set_level(logging.ERROR)
    mock_stop_service.return_value = True
    mock_install_run.return_value = True
    mock_podman_utils.list_expected_podman_container_images.return_value = [
        faker.slug() for _ in range(2)
    ]
    mock_podman_utils.pull_image.side_effect = [False for _ in range(2)]
    mock_args = argparse.Namespace()
    mock_args.no_pull = False
    mock_args.timeout = 0
    mock_args.quiet = False
    assert not upgrade.run(mock_args)
    assert "Failed to pull at least one image" in caplog.messages[-1]
