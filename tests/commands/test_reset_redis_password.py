"""Test the "reset_redis_password" command."""

import logging
from unittest import mock

from quipucordsctl.commands import reset_redis_password


@mock.patch.object(reset_redis_password.podman_utils, "secret_exists")
def test_redis_password_is_set(mock_secret_exists):
    """Test redis_password_is_set just wraps secret_exists."""
    assert reset_redis_password.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(
        reset_redis_password.REDIS_PASSWORD_PODMAN_SECRET_NAME
    )


@mock.patch.object(reset_redis_password.podman_utils, "set_secret")
@mock.patch.object(reset_redis_password.shell_utils, "confirm")
@mock.patch.object(reset_redis_password.secrets, "generate_random_secret")
@mock.patch.object(reset_redis_password.secrets, "prompt_secret")
def test_reset_redis_password_run_success(  # noqa: PLR0913
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_set_secret,
    good_secret,
):
    """Test reset_redis_password.run is successful with default (no prompt) args."""
    mock_args = mock.Mock()
    mock_args.prompt = False
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = True

    assert reset_redis_password.run(mock_args)
    mock_set_secret.assert_called_once_with(
        reset_redis_password.REDIS_PASSWORD_PODMAN_SECRET_NAME, good_secret
    )
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup


@mock.patch.object(reset_redis_password.podman_utils, "set_secret")
@mock.patch.object(reset_redis_password.shell_utils, "confirm")
@mock.patch.object(reset_redis_password.secrets, "prompt_secret")
def test_reset_redis_password_run_with_prompts_success(  # noqa: PLR0913
    mock_prompt_password,
    mock_confirm,
    mock_set_secret,
    good_secret,
):
    """Test reset_redis_password.run is successful with user input prompts."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.return_value = True  # act like use enters 'y'
    mock_set_secret.return_value = True
    mock_prompt_password.return_value = good_secret

    assert reset_redis_password.run(mock_args)
    mock_prompt_password.assert_called_once()
    mock_set_secret.assert_called_once_with(
        reset_redis_password.REDIS_PASSWORD_PODMAN_SECRET_NAME, good_secret
    )
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_redis_password.podman_utils, "set_secret")
@mock.patch.object(reset_redis_password.shell_utils, "confirm")
@mock.patch.object(reset_redis_password.secrets, "prompt_secret")
def test_reset_redis_password_run_decline_manual_input(  # noqa: PLR0913
    mock_prompt_password,
    mock_confirm,
    mock_set_secret,
):
    """Test reset_redis_password.run if user declines manual input confirmation."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.return_value = False  # act like use enters 'n'

    assert not reset_redis_password.run(mock_args)
    mock_prompt_password.assert_not_called()
    mock_set_secret.assert_not_called()
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_redis_password.podman_utils, "set_secret")
@mock.patch.object(reset_redis_password.shell_utils, "confirm")
@mock.patch.object(reset_redis_password.secrets, "generate_random_secret")
@mock.patch.object(reset_redis_password.secrets, "prompt_secret")
def test_reset_redis_password_run_fails_set_secret(  # noqa: PLR0913
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_set_secret,
    good_secret,
    caplog,
):
    """Test reset_redis_password.run when set_secret fails unexpectedly."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.prompt = False
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = False  # might happen in a race condition

    assert not reset_redis_password.run(mock_args)
    mock_set_secret.assert_called_once()
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup
    assert "The Redis password was not updated." == caplog.messages[0]
