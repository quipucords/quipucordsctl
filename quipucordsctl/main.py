"""Main command-line entrypoint."""

import argparse
import logging

from . import settings
from .commands import install

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog=settings.PROGRAM_NAME)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help="Increase verbose output",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        default=0,
        help="Quiet output (overrides `-v`/`--verbose`)",
    )

    parser.add_argument(
        "-c",
        "--override-conf-dir",
        dest="override_conf_dir",
        help="Override configuration directory",
        # TODO specify a type that enforces a valid directory path.
    )

    subparsers = parser.add_subparsers(dest="command")
    # TODO load subparsers dynamically from commands package.

    subparsers.add_parser(
        "install", help=f"Install the {settings.SERVER_SOFTWARE_NAME} server"
    )
    # TODO more arguments for this subparser.

    subparsers.add_parser(
        "uninstall", help=f"Uninstall the {settings.SERVER_SOFTWARE_NAME} server"
    )
    # TODO more arguments for this subparser.

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
    parser = create_parser()
    args = parser.parse_args()
    configure_logging(args.verbosity, args.quiet)

    # TODO load commands dynamically from commands package.
    if args.command == "install":
        install.run(override_conf_dir=args.override_conf_dir)
    elif args.command == "uninstall":
        raise NotImplementedError
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
