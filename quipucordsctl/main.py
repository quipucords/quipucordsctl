"""Main command-line entrypoint."""

import argparse

from . import PROGRAM_NAME, SERVER_SOFTWARE_NAME


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME)
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-c",
        "--override-conf-dir",
        dest="override_conf_dir",
        help="Override configuration directory",
    )

    subparsers = parser.add_subparsers(dest="command")
    # TODO load subparsers dynamically from commands package.

    subparsers.add_parser("install", help=f"Install the {SERVER_SOFTWARE_NAME} server")
    # TODO more arguments for this subparser.

    subparsers.add_parser(
        "uninstall", help=f"Uninstall the {SERVER_SOFTWARE_NAME} server"
    )
    # TODO more arguments for this subparser.

    return parser


def main():
    """Run the program with arguments from the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        print("Verbose mode enabled.")

    if args.command == "install":
        raise NotImplementedError
    elif args.command == "uninstall":
        raise NotImplementedError
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
