"""Test the main module."""

from quipucordsctl import main


def test_create_parser_and_parse():
    """Test the constructed argument parser."""
    parser = main.create_parser()

    # Simplest no-arg invocation.
    parsed_args = parser.parse_args([])
    assert not parsed_args.command
    assert not parsed_args.verbose

    # Many-args invocation
    # TODO use a TemporaryDirectory and assert bogus paths raise errors.
    override_conf_dir = "/bogus/path"
    command = "install"
    parsed_args = parser.parse_args(["-v", "-c", override_conf_dir, command])
    assert parsed_args.verbose
    assert parsed_args.override_conf_dir == override_conf_dir
    assert parsed_args.command == command
