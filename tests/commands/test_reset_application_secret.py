"""Test the "reset_application_secret" command."""

import logging
from unittest import mock

from quipucordsctl.commands import reset_application_secret


def test_application_secret_is_set():
    """Test placeholder for application_secret_is_set."""
    assert not reset_application_secret.application_secret_is_set()


@mock.patch.object(reset_application_secret.podman_utils, "set_secret")
@mock.patch.object(reset_application_secret.podman_utils, "secret_exists")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret.secrets, "generate_random_secret")
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
def test_reset_application_secret_run_fails_set_secret(  # noqa: PLR0913
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
    caplog,
):
    """Test reset_application_secret.run when set_secret fails unexpectedly."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.prompt = False
    mock_secret_exists.return_value = False  # act like first-time setup
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = False  # might happen in a race condition

    assert not reset_application_secret.run(mock_args)
    mock_secret_exists.assert_called_once()
    mock_set_secret.assert_called_once()
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup
    assert "The application secret key was not updated." == caplog.messages[0]


@mock.patch.object(reset_application_secret.podman_utils, "set_secret")
@mock.patch.object(reset_application_secret.podman_utils, "secret_exists")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret.secrets, "generate_random_secret")
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
def test_reset_application_secret_run_success(  # noqa: PLR0913
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
):
    """Test reset_application_secret.run is successful with default (no prompt) args."""
    mock_args = mock.Mock()
    mock_args.prompt = False
    mock_secret_exists.return_value = False  # act like first-time setup
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = True

    assert reset_application_secret.run(mock_args)
    mock_secret_exists.assert_called_once_with(
        reset_application_secret.SESSION_SECRET_PODMAN_SECRET_NAME
    )
    mock_set_secret.assert_called_once_with(
        reset_application_secret.SESSION_SECRET_PODMAN_SECRET_NAME, good_secret, False
    )
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup


@mock.patch.object(reset_application_secret.podman_utils, "set_secret")
@mock.patch.object(reset_application_secret.podman_utils, "secret_exists")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
def test_reset_application_secret_run_with_prompts_success(  # noqa: PLR0913
    mock_prompt_password,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
):
    """Test reset_application_secret.run is successful with user input prompts."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.return_value = True  # act like use always enters 'y'
    mock_secret_exists.return_value = True
    mock_set_secret.return_value = True
    mock_prompt_password.return_value = good_secret

    assert reset_application_secret.run(mock_args)
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_called_once()
    mock_set_secret.assert_called_once_with(
        reset_application_secret.SESSION_SECRET_PODMAN_SECRET_NAME, good_secret, True
    )
    assert len(mock_confirm.call_args_list) == 2


@mock.patch.object(reset_application_secret.podman_utils, "set_secret")
@mock.patch.object(reset_application_secret.podman_utils, "secret_exists")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
def test_reset_application_secret_run_decline_replace_existing(  # noqa: PLR0913
    mock_prompt_password,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
):
    """Test reset_application_secret.run if user declines to replace existing secret."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.return_value = False  # act like use always enters 'n'

    assert not reset_application_secret.run(mock_args)
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_not_called()
    mock_set_secret.assert_not_called()
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_application_secret.podman_utils, "set_secret")
@mock.patch.object(reset_application_secret.podman_utils, "secret_exists")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
def test_reset_application_secret_run_decline_manual_input(  # noqa: PLR0913
    mock_prompt_password,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
):
    """Test reset_application_secret.run if user declines manual input confirmation."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.side_effect = [True, False]  # act like use enters 'y' then 'n'

    assert not reset_application_secret.run(mock_args)
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_not_called()
    mock_set_secret.assert_not_called()
    assert len(mock_confirm.call_args_list) == 2
