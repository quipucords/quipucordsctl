"""Test the "reset_application_secret" command."""

import logging
from unittest import mock

import pytest

from quipucordsctl.commands import reset_application_secret


@pytest.fixture
def good_secret(faker):
    """Generate a "good" secret that should pass validation."""
    return faker.password(
        length=reset_application_secret.SECRET_MIN_LENGTH,
        special_chars=True,
        digits=True,
        upper_case=True,
        lower_case=True,
    )


@pytest.fixture
def bad_secret(faker):
    """Generate a "bad" secret that should fail validation."""
    return faker.password(
        length=reset_application_secret.SECRET_MIN_LENGTH // 2,  # too short
        special_chars=True,
        digits=True,
        upper_case=True,
        lower_case=True,
    )


def test_application_secret_is_set():
    """Test placeholder for application_secret_is_set."""
    assert not reset_application_secret.application_secret_is_set()


@pytest.mark.parametrize(
    "new_secret,confirm_secret,expected_result",
    [
        (
            "123456789012345678901234567890123456789012345678901234567890abcd",
            "123456789012345678901234567890123456789012345678901234567890ABCD",
            False,  # need to match case-sensitive
        ),
        (
            "1234567890123456789012345678901234567890123456789012345678901234",
            "1234567890123456789012345678901234567890123456789012345678901234",
            False,  # needs a letter
        ),
        (
            "abcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcd",
            "abcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcd",
            False,  # needs a number
        ),
        ("abcd1234!", "abcd1234!", False),  # too short
        (
            "123456789012345678901234567890123456789012345678901234567890abcd",
            "123456789012345678901234567890123456789012345678901234567890abcd",
            True,  # this one is fine
        ),
        (
            "My favorite starship is the USS Enterprise, registry NCC-1701-D.",
            "My favorite starship is the USS Enterprise, registry NCC-1701-D.",
            True,  # spaces and punctuation are fine too
        ),
        (
            "123456789012345678901234567890123456789012345678901234567890abcdefghij",
            "123456789012345678901234567890123456789012345678901234567890abcdefghij",
            True,  # longer than minimum is fine too
        ),
    ],
)
def test_check_secret(new_secret, confirm_secret, expected_result):
    """Test check_secret requires sufficiently complex inputs."""
    assert (
        reset_application_secret.check_secret(new_secret, confirm_secret)
        == expected_result
    )


@mock.patch.object(reset_application_secret.getpass, "getpass")
def test_prompt_secret_success(mock_getpass, good_secret):
    """Test prompt_secret with successful entry."""
    mock_getpass.side_effect = [good_secret, good_secret]
    assert reset_application_secret.prompt_secret() == good_secret
    mock_getpass.assert_has_calls(
        [
            mock.call("Enter new server application secret key: "),
            mock.call("Confirm new server application secret key: "),
        ]
    )


@mock.patch.object(reset_application_secret.getpass, "getpass")
def test_prompt_secret_fail_check_secret(mock_getpass, bad_secret, caplog):
    """Test prompt_secret with input that fails check_secret."""
    caplog.set_level(logging.ERROR)
    mock_getpass.side_effect = [bad_secret, bad_secret]

    assert reset_application_secret.prompt_secret() is None
    assert len(caplog.messages) == 2
    assert caplog.messages[-1] == "Application secret key was not updated."


@mock.patch.object(reset_application_secret.shell_utils, "get_podman_client")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret, "prompt_secret")
def test_reset_application_secret_run_success(  # noqa: PLR0913
    mock_prompt_password, mock_confirm, mock_get_podman_client, good_secret, capsys
):
    """Test reset_application_secret.run is successful with default (no prompt) args."""
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_args.prompt = False

    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = False  # act like first-time setup

    assert reset_application_secret.run(mock_args)
    mock_podman_client.secrets.exists.assert_called_once_with(
        reset_application_secret.PODMAN_SECRET_NAME
    )
    mock_prompt_password.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup


@mock.patch.object(reset_application_secret.shell_utils, "get_podman_client")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret, "prompt_secret")
def test_reset_application_secret_run_with_prompts_success(  # noqa: PLR0913
    mock_prompt_password, mock_confirm, mock_get_podman_client, good_secret, capsys
):
    """Test reset_application_secret.run is successful with user input prompts."""
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_args.prompt = True  # require user to confirm

    mock_confirm.return_value = True  # act like use always enters 'y'

    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True  # require user to confirm

    assert reset_application_secret.run(mock_args)
    mock_podman_client.secrets.exists.assert_called_once_with(
        reset_application_secret.PODMAN_SECRET_NAME
    )
    mock_podman_client.secrets.remove.assert_called_once_with(
        reset_application_secret.PODMAN_SECRET_NAME
    )
    mock_podman_client.secrets.create.assert_called_once_with(
        reset_application_secret.PODMAN_SECRET_NAME, mock_prompt_password.return_value
    )
    mock_prompt_password.assert_called_once()
    assert len(mock_confirm.call_args_list) == 2


@mock.patch.object(reset_application_secret.shell_utils, "get_podman_client")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret, "prompt_secret")
def test_reset_application_secret_run_decline_replace_existing(  # noqa: PLR0913
    mock_prompt_password, mock_confirm, mock_get_podman_client, capsys
):
    """Test reset_application_secret.run if user declines to replace existing secret."""
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_args.prompt = True  # require user to confirm

    mock_confirm.return_value = False  # act like use always enters 'n'

    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True  # require user to confirm

    assert not reset_application_secret.run(mock_args)
    mock_podman_client.secrets.exists.assert_called_once_with(
        reset_application_secret.PODMAN_SECRET_NAME
    )
    mock_podman_client.secrets.remove.assert_not_called()
    mock_podman_client.secrets.create.assert_not_called()
    mock_prompt_password.assert_not_called()
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_application_secret.shell_utils, "get_podman_client")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret, "prompt_secret")
def test_reset_application_secret_run_decline_manual_input(  # noqa: PLR0913
    mock_prompt_password, mock_confirm, mock_get_podman_client, capsys
):
    """Test reset_application_secret.run if user declines manual input confirmation."""
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_args.prompt = True  # require user to confirm

    mock_confirm.side_effect = [True, False]  # act like use enters 'y' then 'n'

    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True  # require user to confirm

    assert not reset_application_secret.run(mock_args)
    mock_podman_client.secrets.exists.assert_called_once_with(
        reset_application_secret.PODMAN_SECRET_NAME
    )
    mock_podman_client.secrets.remove.assert_not_called()
    mock_podman_client.secrets.create.assert_not_called()
    mock_prompt_password.assert_not_called()
    assert len(mock_confirm.call_args_list) == 2
