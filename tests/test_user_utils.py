"""Test the user_utils module."""

from unittest import mock

import pytest

from quipucordsctl import settings, user_utils


def test_get_username_known_uid():
    """Test get_username returns the name from the passwd database."""
    with mock.patch.object(user_utils.pwd, "getpwuid") as mock_getpwuid:
        mock_getpwuid.return_value.pw_name = "potatoboi"
        assert user_utils.get_username(1234) == "potatoboi"
    mock_getpwuid.assert_called_once_with(1234)


def test_get_username_no_passwd_entry():
    """Test get_username falls back to the uid when it has no passwd entry."""
    with mock.patch.object(user_utils.pwd, "getpwuid", side_effect=KeyError):
        assert user_utils.get_username(1234) == "1234"


@pytest.mark.parametrize(
    "uid,euid,expected",
    (
        (0, 0, True),  # sudo, su, sudo su, root login, machinectl, systemd-run
        (0, 1000, True),  # root process that dropped only its effective uid
        (1000, 0, True),  # setuid-root executable
        (1000, 1000, False),  # the only acceptable case
    ),
)
def test_is_root_uid_and_euid_combinations(uid, euid, expected):
    """Test is_root considers both the real and the effective uid."""
    with (
        mock.patch.object(user_utils.os, "getuid", return_value=uid),
        mock.patch.object(user_utils.os, "geteuid", return_value=euid),
    ):
        assert user_utils.is_root() is expected


def test_describe_current_user_uid_matches_euid():
    """Test describe_current_user reports the name and uid."""
    with (
        mock.patch.object(user_utils.os, "getuid", return_value=1000),
        mock.patch.object(user_utils.os, "geteuid", return_value=1000),
        mock.patch.object(user_utils, "get_username", return_value="potatoboi"),
    ):
        description = user_utils.describe_current_user()
    assert description == "potatoboi (uid 1000)"


def test_describe_current_user_differing_euid():
    """Test describe_current_user reports both uids when they differ."""
    with (
        mock.patch.object(user_utils.os, "getuid", return_value=1000),
        mock.patch.object(user_utils.os, "geteuid", return_value=0),
        mock.patch.object(
            user_utils, "get_username", side_effect=lambda uid: f"user{uid}"
        ),
    ):
        description = user_utils.describe_current_user()
    assert description == "user1000 (uid 1000), effectively user0 (euid 0)"


def test_ensure_not_root_happy_path():
    """Test ensure_not_root does nothing for an unprivileged user."""
    with mock.patch.object(user_utils, "is_root", return_value=False):
        assert user_utils.ensure_not_root() is None


def test_ensure_not_root_raises_for_root():
    """Test ensure_not_root raises a helpful error for the root user."""
    with (
        mock.patch.object(user_utils, "is_root", return_value=True),
        pytest.raises(user_utils.RunningAsRootError) as exc_info,
    ):
        user_utils.ensure_not_root()

    message = str(exc_info.value)
    assert settings.PROGRAM_NAME in message
    assert "sudo" in message
