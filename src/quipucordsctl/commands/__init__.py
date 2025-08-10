"""Package of mostly self-contained commands.

The CLI loads the modules in this package dynamically at startup.
Valid command modules in this package should implement an interface like the following:

    __doc__ = "Perform magic."

    def setup_parser(parser: argparse.ArgumentParser) -> None:
        # Optional additions to this command's argparse subparser.
        # For example:
        parser.add_argument("-x", action="store_true", help="Enable effects")

    def run(args: argparse.Namespace) -> None:
        # Implementation of this command's functionality.
        # For example"
        shell_utils.run_command(["echo", "hello"])

The module's name will be the CLI's positional argument to invoke the command.
The module's __doc__ will be the help text for the CLI's help command.
For example, invoking `quipucordsctl --help` with the example code above in
a module file named `magic.py` may produce output like the following:

    $ quipucordsctl --help
    usage: quipucordsctl [-h] {install,magic} ...

    positional arguments:
      {install,magic}
        install        Install the Quipucords server.
        magic          Perform magic.

    options:
      -h, --help       show this help message and exit

    $ quipucordsctl magic --help
    usage: quipucordsctl magic [-h] [-x]

    options:
      -h, --help  show this help message and exit
      -x          Enable effects

If the module has attribute `NOT_A_COMMAND=True` set, it will not be included
by argparse as a valid positional argument.
"""
