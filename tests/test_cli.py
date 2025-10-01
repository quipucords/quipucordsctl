"""Test the cli module."""

import logging
from unittest import mock
from unittest.mock import MagicMock

import pytest

from quipucordsctl import cli


def test_load_commands():
    """Test some known commands are loaded and returned."""
    from quipucordsctl.commands import install as install_module  # noqa: PLC0415
    from quipucordsctl.commands import uninstall as uninstall_module  # noqa: PLC0415

    commands = cli.load_commands()
    assert "install" in commands
    assert "uninstall" in commands
    assert commands["install"] == install_module
    assert commands["uninstall"] == uninstall_module

    assert "__init__" not in commands


def test_create_parser_and_parse(faker):
    """Test the constructed argument parser."""
    mock_command_name = faker.slug()
    mock_command_doc = faker.sentence()
    mock_command = mock.Mock()
    mock_command.__doc__ = mock_command_doc

    parser = cli.create_parser({mock_command_name: mock_command})

    # Simplest no-arg invocation.
    parsed_args = parser.parse_args([])
    assert not parsed_args.command
    assert parsed_args.verbosity == 0
    assert not parsed_args.quiet

    # Many-args invocation
    # TODO use a TemporaryDirectory and assert bogus paths raise errors.
    override_conf_dir = "/bogus/path"
    command = mock_command_name
    parsed_args = parser.parse_args(["-vv", "-q", "-c", override_conf_dir, command])
    assert parsed_args.verbosity == 2
    assert parsed_args.quiet
    assert parsed_args.override_conf_dir == override_conf_dir
    assert parsed_args.command == command


@pytest.mark.parametrize(
    "verbosity,quiet,expected_log_levels",
    [
        [
            # default "no argument" use case
            0,
            False,
            [logging.CRITICAL, logging.ERROR, logging.WARNING],
        ],
        [
            # single "-v" argument
            1,
            False,
            [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO],
        ],
        [
            # two "-v" arguments
            2,
            False,
            [
                logging.CRITICAL,
                logging.ERROR,
                logging.WARNING,
                logging.INFO,
                logging.DEBUG,
            ],
        ],
        [
            # three "-v" arguments
            3,
            False,
            [
                logging.CRITICAL,
                logging.ERROR,
                logging.WARNING,
                logging.INFO,
                logging.DEBUG,
            ],
        ],
        [
            # no "-v" arguments and a "-q" argument
            0,
            True,
            [logging.CRITICAL],
        ],
        [
            # 420 "-v" arguments and a "-q" argument
            # quiet has higher priority than verbose
            420,
            True,
            [logging.CRITICAL],
        ],
    ],
)
def test_configure_logging(
    verbosity: int, quiet: bool, expected_log_levels: list[int], caplog
):
    """Test configure_logging sets appropriate log levels."""
    level = cli.configure_logging(verbosity, quiet)

    messages = {
        logging.CRITICAL: "critical message",
        logging.ERROR: "error message",
        logging.WARNING: "warning message",
        logging.INFO: "info message",
        logging.DEBUG: "debug message",
    }

    with caplog.at_level(level):
        for level, message in messages.items():
            logging.log(level, message)

        assert len(caplog.messages) == len(expected_log_levels)

        for level, message in messages.items():
            if level in expected_log_levels:
                assert message in caplog.messages
            else:
                assert message not in caplog.messages


def test_cli_without_command():
    """Test the cli.run function when no command is given."""
    with mock.patch.object(cli, "create_parser") as mock_create_parser:
        mock_parser = mock_create_parser.return_value
        mock_args = mock_parser.parse_args.return_value
        mock_args.verbosity = 0  # need any int because MagicMock is not int-like
        mock_args.quiet = True
        mock_args.yes = False
        mock_args.command = None

        cli.run()

        mock_parser.print_help.assert_called_once()


def test_cli_nonzero_exit_when_command_fails():
    """Test cli.run exits with non-zero exit code when the command fails."""
    with (
        mock.patch.object(cli, "create_parser") as mock_create_parser,
        mock.patch.object(cli, "load_commands") as mock_load_commands,
        mock.patch.object(cli, "sys") as mock_sys,
    ):
        command_name = "failure"

        mock_parser = mock_create_parser.return_value
        mock_args = mock_parser.parse_args.return_value
        mock_args.command = command_name
        mock_args.verbosity = 0  # need any int because MagicMock is not int-like
        mock_args.yes = False
        mock_args.quiet = False

        mock_command = MagicMock()
        mock_command.run.return_value = False
        mock_load_commands.return_value = {command_name: mock_command}

        cli.run()
        mock_sys.exit.assert_called_once_with(1)


@pytest.mark.parametrize(
    "exception,error_message",
    [
        (Exception("uh oh"), "uh oh"),
        (KeyboardInterrupt, "Exiting due to keyboard interrupt."),
        (EOFError, "Input closed unexpectedly."),
    ],
)
def test_cli_nonzero_exit_when_command_raises_exception(
    exception, error_message, caplog
):
    """Test cli.run exits with non-zero exit code following an exception."""
    with (
        mock.patch.object(cli, "create_parser") as mock_create_parser,
        mock.patch.object(cli, "load_commands") as mock_load_commands,
        mock.patch.object(cli, "sys") as mock_sys,
        caplog.at_level(logging.ERROR),
    ):
        command_name = "failure"

        mock_parser = mock_create_parser.return_value
        mock_args = mock_parser.parse_args.return_value
        mock_args.command = command_name
        mock_args.verbosity = 0  # need any int because MagicMock is not int-like
        mock_args.yes = False
        mock_args.quiet = False

        mock_command = MagicMock()
        mock_command.run.side_effect = exception
        mock_load_commands.return_value = {command_name: mock_command}

        cli.run()
        mock_sys.exit.assert_called_once_with(1)

        assert caplog.messages == [error_message]
