"""Test the "reset_admin_password" command."""

import logging
import uuid
from unittest import mock

import pytest

from quipucordsctl.commands import reset_admin_password


class MysteryError(Exception):
    """Something completely unexpected happened."""

    def __str__(self):
        """Get string representation."""
        return self.__doc__


def test_admin_password_is_set():
    """Test placeholder for admin_password_is_set."""
    assert not reset_admin_password.admin_password_is_set()


@mock.patch.object(reset_admin_password.getpass, "getpass")
@mock.patch.object(reset_admin_password, "check_password")
def test_prompt_password_success(mock_check_password, mock_getpass, faker):
    """Test prompt_password_success with successful entry."""
    fake_password = faker.password(
        length=10, special_chars=True, digits=True, upper_case=True, lower_case=True
    )
    mock_getpass.side_effect = [fake_password, fake_password]
    mock_check_password.return_value = True

    assert reset_admin_password.prompt_password() == fake_password
    mock_getpass.assert_has_calls(
        [
            mock.call("Enter new server login password: "),
            mock.call("Confirm new server login password: "),
        ]
    )
    mock_check_password.assert_called_once_with(fake_password, fake_password)


@mock.patch.object(reset_admin_password.getpass, "getpass")
@mock.patch.object(reset_admin_password, "check_password")
def test_prompt_password_fail_check_password(
    mock_check_password, mock_getpass, faker, caplog
):
    """Test prompt_password_success with input that fails check_password."""
    caplog.set_level(logging.ERROR)
    fake_password = faker.password(
        length=10, special_chars=True, digits=True, upper_case=True, lower_case=True
    )
    mock_getpass.side_effect = [fake_password, fake_password]
    mock_check_password.return_value = False

    assert reset_admin_password.prompt_password() is None
    mock_check_password.assert_called_once_with(fake_password, fake_password)
    assert len(caplog.messages) == 1
    assert caplog.messages[0] == "Password was not updated."


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password, "prompt_password")
def test_reset_admin_password_run_success(mock_prompt_password, mock_popen, caplog):
    """Test reset_admin_password.run is successful."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_password.return_value = password
    mock_process = mock_popen.return_value  # act like oc process succeeded
    mock_process.communicate.return_value = (None, None)
    mock_process.returncode = 0
    assert reset_admin_password.run(mock_args)
    assert len(caplog.messages) == 0


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password, "prompt_password")
def test_reset_admin_password_run_success_verbose_verbose(
    mock_prompt_password, mock_popen, caplog, faker
):
    """Test reset_admin_password.run logs details with 2 --verbose flags."""
    caplog.set_level(logging.DEBUG)
    mock_args = mock.Mock()
    mock_args.verbosity = 2
    password = str(uuid.uuid4())
    mock_prompt_password.return_value = password
    process_stdout = faker.sentence()  # act like oc process succeeded
    mock_process = mock_popen.return_value
    mock_process.communicate.return_value = (process_stdout, None)
    mock_process.returncode = 0
    assert reset_admin_password.run(mock_args)
    assert "created/replaced successfully" in caplog.messages[0]
    assert "stdout" in caplog.messages[1]
    assert process_stdout in caplog.messages[2]


@mock.patch.object(reset_admin_password, "prompt_password")
def test_reset_admin_password_run_bad_password(mock_prompt_password):
    """Test reset_admin_password.run when password fails validation checks."""
    mock_args = mock.Mock()
    mock_prompt_password.return_value = None
    assert not reset_admin_password.run(mock_args)


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password, "prompt_password")
def test_reset_admin_password_run_oc_fails(mock_prompt_password, mock_popen, caplog):
    """Test reset_admin_password.run when the `oc` command fails."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_password.return_value = password
    mock_process = mock_popen.return_value  # act like oc process failed
    mock_process.communicate.return_value = (None, None)
    mock_process.returncode = 1
    assert not reset_admin_password.run(mock_args)
    assert "Failed to create podman secret" in caplog.messages[0]


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password, "prompt_password")
def test_reset_admin_password_run_oc_not_installed(
    mock_prompt_password, mock_popen, caplog
):
    """Test reset_admin_password.run when the `oc` program is not found in the PATH."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_password.return_value = password
    mock_process = mock_popen.return_value  # act like oc program could not be found
    mock_process.communicate.side_effect = FileNotFoundError
    assert not reset_admin_password.run(mock_args)
    assert "command not found" in caplog.messages[0]


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password, "prompt_password")
def test_reset_admin_password_run_truly_unexpected_error(
    mock_prompt_password, mock_popen, caplog
):
    """Test reset_admin_password.run when a truly unexpected error occurs."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_password.return_value = password
    mock_process = mock_popen.return_value
    mock_process.communicate.side_effect = MysteryError
    assert not reset_admin_password.run(mock_args)
    assert "An unexpected error occurred" in caplog.messages[0]
    assert MysteryError.__doc__ in caplog.messages[0]


@pytest.mark.parametrize(
    "new_password,confirm_password,expected_result",
    [
        ("sup3rs3cr3tp4ss", "d0esn0tm4tch", False),  # does no match
        ("admin", "admin", False),  # too short
        ("12345678901234567890", "12345678901234567890", False),  # only numbers
        ("dscpassw0rd", "dscpassw0rd", False),  # forbidden
        ("qpccpassw0rd", "qpcpassw0rd", False),  # forbidden
        ("!@#$%^&*()!@#$%^&*()", "!@#$%^&*()!@#$%^&*()", True),  # ok!
        ("super secret", "super secret", True),  # ok!
        (" hello there ", " hello there ", True),  # ok! we do not trim whitespace
        ("adminadmin", "adminadmin", True),  # ok! similar to username, but not too much
        ("admin12345", "admin12345", True),  # ok! similar to username, but not too much
    ],
)
def test_check_password(new_password, confirm_password, expected_result):
    """Test check_password enforces expected checks."""
    assert (
        reset_admin_password.check_password(new_password, confirm_password)
        == expected_result
    )


@pytest.mark.parametrize(
    "new_password,confirm_password,expected_result",
    [
        ("superadmin", "superadmin", False),  # identical to username
        ("superadmin!", "superadmin!", False),  # still too similar to username
        ("super4dmin!", "super4dmin!", False),  # still too similar to username
        ("loseradmin", "loseradmin", False),  # still too similar to username
        ("sup3r4dm1n!", "sup3r4dm1n!", True),  # different enough
        ("NotTheAdmin", "NotTheAdmin", True),  # different enough
        ("!@#$%^&*()", "!@#$%^&*()", True),  # definitely different enough
    ],
)
def test_check_password_username_similarity(
    new_password, confirm_password, expected_result, mocker
):
    """
    Test check_password_username forbids a password that is too similar to the username.

    This test mocks out the DEFAULT_USERNAME value because the default value of "admin"
    is so short that any password close enough to trigger the similarity condition would
    itself be too short, making this test meaningless. The mocked value "superadmin" is
    long enough for us to assert confidently that this test is hitting the similarity
    check specifically.
    """
    mocker.patch(
        "quipucordsctl.commands.reset_admin_password.DEFAULT_USERNAME", "superadmin"
    )
    assert (
        reset_admin_password.check_password(new_password, confirm_password)
        == expected_result
    )
