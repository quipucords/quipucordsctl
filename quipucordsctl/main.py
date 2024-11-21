"""Main command-line entrypoint."""

import argparse

from . import settings
from .commands import install


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog=settings.PROGRAM_NAME)
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
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


def main():
    """Run the program with arguments from the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        print("Verbose mode enabled.")

    # TODO load commands dynamically from commands package.
    if args.command == "install":
        install.run(override_conf_dir=args.override_conf_dir, verbose=args.verbose)
    elif args.command == "uninstall":
        raise NotImplementedError
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
