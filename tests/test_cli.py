"""Test the cli module."""

import logging
from unittest import mock
from unittest.mock import MagicMock

import pytest

from quipucordsctl import argparse_utils, cli


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
    mock_command.get_display_group = mock.Mock(
        return_value=argparse_utils.DisplayGroups.OTHER
    )

    parser = cli.create_parser({mock_command_name: mock_command})

    # Check that the mock_command was created under the "other" group.
    argparse_group = next(
        filter(
            lambda _group: _group.title == argparse_utils.DisplayGroups.OTHER.value,
            parser._action_groups,
        )
    )
    action = next(
        filter(
            lambda _action: _action.dest == mock_command_name,
            argparse_group._group_actions,
        )
    )
    assert action is not None
    # If action exists in the filtered group, then it was added correctly.

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
    level = cli.configure_log_level(verbosity, quiet)

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
        mock_args.color = "never"

        mock_command = MagicMock()
        mock_command.run.side_effect = exception
        mock_load_commands.return_value = {command_name: mock_command}

        cli.run()
        mock_sys.exit.assert_called_once_with(1)

        assert caplog.messages == [error_message]


@pytest.mark.parametrize(
    "color_choice,no_color_env,isatty,expected",
    [
        ("always", "", False, True),
        ("always", "", True, True),
        ("always", "1", False, True),
        ("always", "1", True, True),
        ("never", "", False, False),
        ("never", "", True, False),
        ("never", "1", False, False),
        ("never", "1", True, False),
        ("auto", "", False, False),
        ("auto", "", True, True),
        ("auto", "1", False, False),
        ("auto", "1", True, False),
    ],
)
def test_should_use_color(color_choice, no_color_env, isatty, expected, monkeypatch):
    """Test cli.should_use_color respects choice, NO_COLOR env var, and detected tty."""
    monkeypatch.setenv("NO_COLOR", no_color_env)
    fake_stream = mock.Mock()
    fake_stream.isatty.return_value = isatty
    assert cli.should_use_color(color_choice, fake_stream) is expected


def test_ctlloggingformatter_format(faker):
    """Test cli.ctlloggingformatter format with color enabled and high verbosity."""
    datefmt = faker.slug()  # predictable placeholder since datetime changes quickly
    formatter = cli.CtlLoggingFormatter(use_color=True, verbosity=5, datefmt=datefmt)
    message = faker.sentence()
    record = logging.LogRecord(
        name="my_logger",
        level=logging.DEBUG,
        pathname=faker.slug(),
        lineno=faker.pyint(),
        msg=message,
        args=[],
        exc_info=None,
    )
    expected = (
        f"{formatter.LEVEL_STYLES[logging.DEBUG]}"
        f"{datefmt} DEBUG: {message}{formatter.RESET}"
    )
    assert formatter.format(record) == expected


def test_ctlloggingformatter_format_no_color(faker):
    """Test cli.ctlloggingformatter format with color disabled."""
    datefmt = faker.slug()  # predictable placeholder since datetime changes quickly
    formatter = cli.CtlLoggingFormatter(use_color=False, verbosity=5, datefmt=datefmt)
    message = faker.sentence()
    record = logging.LogRecord(
        name="my_logger",
        level=logging.DEBUG,
        pathname=faker.slug(),
        lineno=faker.pyint(),
        msg=message,
        args=[],
        exc_info=None,
    )
    expected = f"{datefmt} DEBUG: {message}"
    assert formatter.format(record) == expected


def test_ctlloggingformatter_format_no_verbosity(faker):
    """Test cli.ctlloggingformatter format with color enabled but no verbosity."""
    formatter = cli.CtlLoggingFormatter(
        use_color=True, verbosity=0, datefmt=faker.slug()
    )
    message = faker.sentence()
    record = logging.LogRecord(
        name="my_logger",
        level=logging.DEBUG,
        pathname=faker.slug(),
        lineno=faker.pyint(),
        msg=message,
        args=[],
        exc_info=None,
    )
    expected = (
        f"{formatter.LEVEL_STYLES[logging.DEBUG]}DEBUG: {message}{formatter.RESET}"
    )
    assert formatter.format(record) == expected


def test_ctlloggingformatter_format_unsupported_level(faker):
    """Test cli.ctlloggingformatter format with unsupported level."""
    formatter = cli.CtlLoggingFormatter(
        use_color=True, verbosity=0, datefmt=faker.slug()
    )
    message = faker.sentence()
    record = logging.LogRecord(
        name="my_logger",
        level=logging.NOTSET,
        pathname=faker.slug(),
        lineno=faker.pyint(),
        msg=message,
        args=[],
        exc_info=None,
    )
    expected = f"NOTSET: {message}"
    assert formatter.format(record) == expected


def test_install_console_handler(caplog):
    """Test cli.install_console_handler adds the expected handler."""
    caplog.set_level(logging.DEBUG)
    with mock.patch.object(cli, "logging") as mock_logging:
        mock_root_logger = mock_logging.getLogger.return_value
        mock_root_logger.handlers = []
        mock_handler = mock_logging.StreamHandler.return_value

        cli.install_console_handler(verbosity=0, color="never")

        mock_root_logger.addHandler.assert_called_once()
        mock_handler.setFormatter.assert_called_once()
        assert mock_handler == mock_root_logger.addHandler.call_args[0][0]
        formatter = mock_handler.setFormatter.call_args[0][0]
        assert isinstance(formatter, cli.CtlLoggingFormatter)
        assert formatter.use_color is False

    assert caplog.messages == []


def test_install_console_handler_skips_if_any_handler_exists(caplog):
    """Test cli.install_console_handler skips if any handler is already installed."""
    caplog.set_level(logging.WARNING)
    with mock.patch.object(cli, "logging") as mock_logging:
        mock_root_logger = mock_logging.getLogger.return_value
        mock_root_logger.handlers = [mock.Mock()]
        mock_logging.StreamHandler = mock.Mock

        cli.install_console_handler(verbosity=0, color="never")

        mock_root_logger.addHandler.assert_not_called()

    assert caplog.messages == ["Cannot install log handler due to existing handler."]
