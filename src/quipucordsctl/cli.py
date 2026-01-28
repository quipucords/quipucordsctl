"""Main command-line entrypoint."""

import argparse
import importlib
import logging
import os
import pkgutil
import sys
from gettext import gettext as _
from types import ModuleType

from . import argparse_utils, podman_utils, settings, systemctl_utils

logger = logging.getLogger(__name__)


class CtlLoggingFormatter(logging.Formatter):
    """Custom logging formatter that conditionally adds colors and timestamps."""

    LEVEL_STYLES = {
        logging.DEBUG: "\033[2m",  # dim (grey)
        logging.INFO: "",  # normal
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[31;1m",  # bold red
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool, verbosity: int, datefmt: str):
        log_format = (
            "%(asctime)s %(levelname)s %(name)s:%(lineno)d: %(message)s"
            if verbosity > 3  # noqa: PLR2004
            else "%(asctime)s %(levelname)s: %(message)s"
            if verbosity > 2  # noqa: PLR2004
            else "%(levelname)s: %(message)s"
        )
        super().__init__(fmt=log_format, datefmt=datefmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        """Conditionally format the record with color for logging."""
        line = super().format(record)

        if not self.use_color:
            return line

        if style := self.LEVEL_STYLES.get(record.levelno, ""):
            return f"{style}{line}{self.RESET}"

        return line


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
    parser = argparse.ArgumentParser(
        prog=settings.PROGRAM_NAME,
        usage=_("%(prog)s [OPTIONS...] COMMAND [COMMAND OPTIONS...]"),
        description=_("Configure and manage local %(server_software_name)s services.")
        % {"server_software_name": settings.SERVER_SOFTWARE_NAME},
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help=_("Increase verbose output"),
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        dest="yes",
        default=False,
        help=_("Automatically answer 'y' to all confirmation prompts"),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        default=False,
        help=_("Quiet output (overrides `-v`/`--verbose`)"),
    )
    parser.add_argument(
        "--color",
        "-C",
        choices=("auto", "always", "never"),
        default="auto",
        help=_("Control the use of color in output"),
    )
    parser.add_argument(
        "-c",
        "--override-conf-dir",
        dest="override_conf_dir",
        help=_("Override configuration directory"),
        # TODO specify a type that enforces a valid directory path.
    )

    subparsers = parser.add_subparsers(
        dest="command", help=argparse.SUPPRESS, metavar=""
    )
    argparse_display_groups = {
        argparse_utils.DisplayGroups.MAIN: parser.add_argument_group(
            argparse_utils.DisplayGroups.MAIN.value
        ),
        argparse_utils.DisplayGroups.CONFIG: parser.add_argument_group(
            argparse_utils.DisplayGroups.CONFIG.value
        ),
        argparse_utils.DisplayGroups.DIAGNOSTICS: parser.add_argument_group(
            argparse_utils.DisplayGroups.DIAGNOSTICS.value
        ),
        argparse_utils.DisplayGroups.OTHER: parser.add_argument_group(
            argparse_utils.DisplayGroups.OTHER.value
        ),
    }

    for command_name, command_module in commands.items():
        display_group = (
            getattr(command_module, "get_display_group")()
            if hasattr(command_module, "get_display_group")
            else None
        )
        argparse_display_group = argparse_display_groups.get(
            display_group,
            argparse_display_groups.get(argparse_utils.DisplayGroups.OTHER),
            # OTHER should always exist as a fallback; see the dict above.
        )
        help_text = (
            getattr(command_module, "get_help")()
            if hasattr(command_module, "get_help")
            else None
        )
        description = (
            getattr(command_module, "get_description")()
            if hasattr(command_module, "get_description")
            else None
        )
        epilog = (
            getattr(command_module, "get_epilog")()
            if hasattr(command_module, "get_epilog")
            else None
        )
        argparse_utils.add_command(
            subparsers,
            command_module,
            argparse_display_group,
            command_name,
            help_text,
            description,
            epilog,
        )

    return parser


def should_use_color(color_choice: str, stream) -> bool:
    """Determine whether to use color in output."""
    if color_choice == "always":
        return True
    if color_choice == "never":
        return False
    if os.environ.get("NO_COLOR", None):
        return False
    return stream.isatty()


def configure_log_level(verbosity: int = 0, quiet: bool = False) -> int:
    """
    Configure the base logger.

    Returns the calculated level used to configure the logging module.
    """
    log_level = (
        logging.CRITICAL
        if quiet
        else max(logging.DEBUG, settings.DEFAULT_LOG_LEVEL - (verbosity * 10))
    )
    root = logging.getLogger()
    root.setLevel(log_level)
    return log_level


def install_console_handler(verbosity: int, color: str) -> None:
    """
    Install the custom console logging handler.

    This function should be called exactly once, only at program startup.
    """
    root = logging.getLogger()

    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        # Early return in case handlers have already been installed.
        logger.warning(_("Cannot install log handler due to existing handler."))
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        CtlLoggingFormatter(
            use_color=should_use_color(color, handler.stream),
            verbosity=verbosity,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)


def run(install_logging_handlers=False):
    """Run the program with arguments from the CLI."""
    commands = load_commands()
    parser = create_parser(commands)
    args = parser.parse_args()

    configure_log_level(args.verbosity, args.quiet)
    if install_logging_handlers:
        # Conditionally install handlers to allow
        # unit tests to operate without them.
        install_console_handler(args.verbosity, args.color)

    settings.runtime.update(yes=args.yes, quiet=args.quiet)

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
        except podman_utils.PodmanIsNotReadyError as e:
            # can occur if podman is not available or running
            print()
            logger.error(e)
            sys.exit(1)
        except systemctl_utils.NoSystemdUserSessionError as e:
            # systemctl user session is not available
            print()
            logger.error(e)
            sys.exit(1)
        except Exception as e:  # noqa: BLE001
            print()  # new line for cleaner output before logger
            logger.exception(e)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    run()
