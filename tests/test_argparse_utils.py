"""Test the quipucordsctl.argparse_utils module."""

import argparse
from unittest import mock

import pytest

from quipucordsctl import argparse_utils


@pytest.mark.parametrize("value,expected", (("0", 0), ("420", 420)))
def test_non_negative_integer(value, expected):
    """Test non_negative_integer happy paths."""
    assert argparse_utils.non_negative_integer(value) == expected


@pytest.mark.parametrize("value", ("-1", "4.2", "e", "", " "))
def test_non_negative_integer_invalid(value):
    """Test non_negative_integer happy paths."""
    with pytest.raises(argparse.ArgumentTypeError):
        argparse_utils.non_negative_integer(value)


def test_add_command(faker):
    """Test add_command correctly adds to a specific action group for help display."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser.add_argument_group(faker.slug())  # extra to force checking multiple groups
    middle_argument_group = parser.add_argument_group(faker.slug())
    parser.add_argument_group(faker.slug())  # extra to force checking multiple groups

    mock_command = mock.Mock()
    command_name = faker.slug()
    command_help = faker.sentence()
    command_description = faker.sentence()
    command_epilog = faker.sentence()

    argparse_utils.add_command(
        subparsers,
        mock_command,
        middle_argument_group,
        command_name,
        command_help,
        command_description,
        command_epilog,
    )

    argparse_group = next(
        filter(
            lambda _group: _group.title == middle_argument_group.title,
            parser._action_groups,
        )
    )
    action = next(
        filter(
            lambda _action: _action.dest == command_name,
            argparse_group._group_actions,
        )
    )
    # If action is found in the filtered action group, then it was added as expected.
    # This is an implicit assertion by virtue of the "next"s not raising StopIteration.

    mock_command.setup_parser.assert_called_once()
    assert action.dest == command_name
    assert action.help == command_help
    assert subparsers.choices[command_name].description == command_description
    assert subparsers.choices[command_name].epilog == command_epilog
