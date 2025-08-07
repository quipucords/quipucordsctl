"""Test the quipucordsctl.secrets module."""

import logging
from unittest import mock

import pytest

from quipucordsctl import secrets


@mock.patch.object(secrets.getpass, "getpass")
def test_prompt_secret_success(mock_getpass, good_secret):
    """Test prompt_secret with successful entry."""
    mock_getpass.side_effect = [good_secret, good_secret]
    assert secrets.prompt_secret("potato") == good_secret
    mock_getpass.assert_has_calls(
        [
            mock.call("Enter new potato: "),
            mock.call("Confirm new potato: "),
        ]
    )


@pytest.mark.parametrize(
    "new_secret,kwargs,expected_result",
    [
        ("1234567890123456", {}, False),  # cannot be only numbers
        ("1234567890!@#$%^", {}, False),  # needs a letter
        ("abcdefghijabcdef", {}, False),  # needs a number
        ("abcd1234", {}, False),  # too short
        ("1234567890abcdef", {}, True),  # OK with defaults
        ("abcd1234", {"min_length": 4}, True),  # OK with custom min_length
        ("What? 1 + 2 = 3!", {}, True),  # spaces and punctuation are OK
        ("123456789012345678901234567890abcd", {}, True),  # longer than minimum is OK
        (
            "1234567890abcdef",
            {"blocklist": ["hello", "1234567890abcdef", "world"]},
            False,  # cannot be in blocklist
        ),
        (
            "1234567890abcdef",
            {
                "check_similar": secrets.SimilarValueCheck(
                    "1234567890abcde!", "name of other value", 0.2
                ),
            },
            False,  # cannot be too similar to given comparison value
        ),
    ],
)
def test_check_secret(new_secret, kwargs, expected_result):
    """Test check_secret requires sufficiently complex inputs."""
    assert secrets.check_secret(new_secret, "my secret", **kwargs) == expected_result


@mock.patch.object(secrets.getpass, "getpass")
def test_prompt_secret(mock_getpass, good_secret, caplog):
    """Test prompt_secret succeeds when input passes check_secret."""
    caplog.set_level(logging.ERROR)
    mock_getpass.side_effect = [good_secret, good_secret]

    assert secrets.prompt_secret("potato")
    assert len(caplog.messages) == 0


@mock.patch.object(secrets.getpass, "getpass")
def test_prompt_secret_fails_mismatch(mock_getpass, good_secret, bad_secret, caplog):
    """Test prompt_secret fails when inputs don't match."""
    caplog.set_level(logging.ERROR)
    mock_getpass.side_effect = [good_secret, good_secret[::-1]]

    assert not secrets.prompt_secret("potato")
    assert len(caplog.messages) == 1
    assert "Your potato inputs do not match." in caplog.messages


@mock.patch.object(secrets.getpass, "getpass")
def test_prompt_secret_fails_check_secret(mock_getpass, bad_secret, caplog):
    """Test prompt_secret fails when input fails check_secret."""
    caplog.set_level(logging.ERROR)
    mock_getpass.side_effect = [bad_secret, bad_secret]

    assert secrets.prompt_secret("potato") is None
    assert len(caplog.messages) == 3
    assert "Your potato must be at least 16 characters long." in caplog.messages
    assert "Your potato must contain a number." in caplog.messages
    assert "Your potato must contain a letter." in caplog.messages
