"""Main command-line entrypoint."""

import argparse
import importlib
import logging
import pkgutil
import sys
from gettext import gettext as _
from types import ModuleType

from . import settings

logger = logging.getLogger(__name__)


def load_commands() -> dict[str, ModuleType]:
    """Dynamically load command modules."""
    commands = {}
    for __, module_name, __ in pkgutil.iter_modules([settings.COMMANDS_PACKAGE_PATH]):
        module = importlib.import_module(f"quipucordsctl.commands.{module_name}")
        if not getattr(module, "NOT_A_COMMAND", False):
            commands[module_name] = module
    return commands


def create_parser(commands: dict[str, ModuleType]) -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog=settings.PROGRAM_NAME)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help=_("Increase verbose output"),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        default=0,
        help=_("Quiet output (overrides `-v`/`--verbose`)"),
    )

    parser.add_argument(
        "-c",
        "--override-conf-dir",
        dest="override_conf_dir",
        help=_("Override configuration directory"),
        # TODO specify a type that enforces a valid directory path.
    )

    subparsers = parser.add_subparsers(dest="command")
    for command_name, command_module in commands.items():
        command_parser = subparsers.add_parser(
            command_name, help=command_module.get_help()
        )
        if hasattr(command_module, "setup_parser"):
            command_module.setup_parser(command_parser)

    return parser


def configure_logging(verbosity: int = 0, quiet: bool = False) -> int:
    """
    Configure the base logger.

    Returns the calculated level used to configure the logging module.
    """
    log_level = (
        logging.CRITICAL
        if quiet
        else max(logging.DEBUG, settings.DEFAULT_LOG_LEVEL - (verbosity * 10))
    )
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=log_level,
        encoding="utf-8",
    )
    return log_level


def main():
    """Run the program with arguments from the CLI."""
    commands = load_commands()
    parser = create_parser(commands)
    args = parser.parse_args()
    configure_logging(args.verbosity, args.quiet)

    if args.command in commands:
        try:
            if not commands[args.command].run(args):
                sys.exit(1)
        except SystemExit:
            raise
        except KeyboardInterrupt:  # can occur via control-c input
            print()  # new line for cleaner output before logger
            logger.error(_("Exiting due to keyboard interrupt."))
            sys.exit(1)
        except EOFError:  # can occur via control-d input
            print()  # new line for cleaner output before logger
            logger.error(_("Input closed unexpectedly."))
            sys.exit(1)
        except Exception as e:  # noqa: BLE001
            print()  # new line for cleaner output before logger
            logger.exception(e)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
