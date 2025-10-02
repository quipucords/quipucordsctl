"""Test the "reset_database_password" command."""

import argparse
import logging
from unittest import mock

from quipucordsctl.commands import reset_database_password


@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
def test_database_password_is_set(mock_secret_exists):
    """Test database_password_is_set just wraps secret_exists."""
    assert reset_database_password.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(
        reset_database_password.DATABASE_PASSWORD_PODMAN_SECRET_NAME
    )


@mock.patch.object(reset_database_password.podman_utils, "set_secret")
@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
@mock.patch.object(reset_database_password.shell_utils, "confirm")
@mock.patch.object(reset_database_password.secrets, "generate_random_secret")
@mock.patch.object(reset_database_password.secrets, "prompt_secret")
@mock.patch.object(reset_database_password.secrets, "read_from_env")
def test_reset_database_password_run_fails_set_secret(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
    caplog,
):
    """Test reset_database_password.run when set_secret fails unexpectedly."""
    caplog.set_level(logging.ERROR)
    args = argparse.Namespace()
    args.prompt = False
    mock_secret_exists.return_value = False  # act like first-time setup
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = False  # might happen in a race condition
    mock_read_from_env.return_value = None, False

    assert not reset_database_password.run(args)
    mock_read_from_env.assert_called_once()
    mock_secret_exists.assert_called_once()
    mock_set_secret.assert_called_once()
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup
    assert "The database password was not updated." == caplog.messages[0]


@mock.patch.object(reset_database_password.podman_utils, "set_secret")
@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
@mock.patch.object(reset_database_password.shell_utils, "confirm")
@mock.patch.object(reset_database_password.secrets, "generate_random_secret")
@mock.patch.object(reset_database_password.secrets, "prompt_secret")
@mock.patch.object(reset_database_password.secrets, "read_from_env")
def test_reset_database_password_run_success(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
):
    """Test reset_database_password.run is successful with default (no prompt) args."""
    args = argparse.Namespace()
    args.prompt = False
    mock_secret_exists.return_value = False  # act like first-time setup
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = True
    mock_read_from_env.return_value = None, False

    assert reset_database_password.run(args)
    mock_read_from_env.assert_called_once()
    mock_secret_exists.assert_called_once_with(
        reset_database_password.DATABASE_PASSWORD_PODMAN_SECRET_NAME
    )
    mock_set_secret.assert_called_once_with(
        reset_database_password.DATABASE_PASSWORD_PODMAN_SECRET_NAME,
        good_secret,
        False,
    )
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup


@mock.patch.object(reset_database_password.podman_utils, "set_secret")
@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
@mock.patch.object(reset_database_password.shell_utils, "confirm")
@mock.patch.object(reset_database_password.secrets, "prompt_secret")
@mock.patch.object(reset_database_password.secrets, "read_from_env")
def test_reset_database_password_run_with_prompts_success(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_password,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
):
    """Test reset_database_password.run is successful with user input prompts."""
    args = argparse.Namespace()
    args.prompt = True  # require user to confirm
    mock_confirm.return_value = True  # act like use always enters 'y'
    mock_secret_exists.return_value = True
    mock_set_secret.return_value = True
    mock_prompt_password.return_value = good_secret

    assert reset_database_password.run(args)
    mock_read_from_env.assert_not_called()  # because user asked to be prompted
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_called_once()
    mock_set_secret.assert_called_once_with(
        reset_database_password.DATABASE_PASSWORD_PODMAN_SECRET_NAME,
        good_secret,
        True,
    )
    assert len(mock_confirm.call_args_list) == 2


@mock.patch.object(reset_database_password.podman_utils, "set_secret")
@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
@mock.patch.object(reset_database_password.shell_utils, "confirm")
@mock.patch.object(reset_database_password.secrets, "prompt_secret")
@mock.patch.object(reset_database_password.secrets, "read_from_env")
def test_reset_database_password_run_decline_replace_existing(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_password,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
):
    """Test reset_database_password.run if user declines to replace existing secret."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.return_value = False  # act like use always enters 'n'

    assert not reset_database_password.run(mock_args)
    mock_read_from_env.assert_not_called()  # because user asked to be prompted
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_not_called()
    mock_set_secret.assert_not_called()
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_database_password.podman_utils, "set_secret")
@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
@mock.patch.object(reset_database_password.shell_utils, "confirm")
@mock.patch.object(reset_database_password.secrets, "prompt_secret")
@mock.patch.object(reset_database_password.secrets, "read_from_env")
def test_reset_database_password_run_decline_manual_input(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_password,
    mock_confirm,
    mock_secret_exists,
    mock_set_secret,
):
    """Test reset_database_password.run if user declines manual input confirmation."""
    mock_args = mock.Mock()
    mock_args.prompt = True  # require user to confirm
    mock_confirm.side_effect = [True, False]  # act like use enters 'y' then 'n'

    assert not reset_database_password.run(mock_args)
    mock_read_from_env.assert_not_called()  # because user asked to be prompted
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_not_called()
    mock_set_secret.assert_not_called()
    assert len(mock_confirm.call_args_list) == 2


@mock.patch.object(reset_database_password.podman_utils, "set_secret")
@mock.patch.object(reset_database_password.podman_utils, "secret_exists")
@mock.patch.object(reset_database_password.shell_utils, "settings")
@mock.patch.object(reset_database_password.secrets, "prompt_secret")
@mock.patch.object(reset_database_password.secrets, "read_from_env")
def test_reset_database_password_headless_mode(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_password,
    mock_settings,
    mock_secret_exists,
    mock_set_secret,
    good_secret,
):
    """Test reset_database_password.run using env vars, yes, and quiet."""
    args = argparse.Namespace()
    mock_settings.yes = True
    mock_settings.quiet = True
    mock_secret_exists.return_value = True
    mock_set_secret.return_value = True
    mock_read_from_env.return_value = good_secret, False

    assert reset_database_password.run(args)
    mock_read_from_env.assert_called_once()
    mock_secret_exists.assert_called_once()
    mock_prompt_password.assert_not_called()
    mock_set_secret.assert_called_once_with(
        reset_database_password.DATABASE_PASSWORD_PODMAN_SECRET_NAME,
        good_secret,
        True,
    )
