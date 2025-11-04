"""Test the quipucordsctl.argparse_utils module."""

import argparse

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
