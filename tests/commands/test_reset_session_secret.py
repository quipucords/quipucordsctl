"""Test the "reset_session_secret" command."""

import argparse
import logging
from unittest import mock

from quipucordsctl.commands import reset_session_secret


@mock.patch.object(reset_session_secret.podman_utils, "secret_exists")
def test_session_secret_is_set(mock_secret_exists):
    """Test session_secret_is_set just wraps secret_exists."""
    assert reset_session_secret.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(
        reset_session_secret.SESSION_SECRET_PODMAN_SECRET_NAME
    )


@mock.patch.object(reset_session_secret.podman_utils, "set_secret")
@mock.patch.object(reset_session_secret.shell_utils, "confirm")
@mock.patch.object(reset_session_secret.secrets, "generate_random_secret")
@mock.patch.object(reset_session_secret.secrets, "prompt_secret")
@mock.patch.object(reset_session_secret.secrets, "read_from_env")
def test_reset_session_secret_run_success(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_set_secret,
    good_secret,
):
    """Test reset_session_secret.run is successful with default (no prompt) args."""
    args = argparse.Namespace()
    args.prompt = False
    mock_read_from_env.return_value = None, False
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = True

    assert reset_session_secret.run(args)
    mock_read_from_env.assert_called_once()
    mock_set_secret.assert_called_once_with(
        reset_session_secret.SESSION_SECRET_PODMAN_SECRET_NAME, good_secret
    )
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup


@mock.patch.object(reset_session_secret.podman_utils, "set_secret")
@mock.patch.object(reset_session_secret.shell_utils, "confirm")
@mock.patch.object(reset_session_secret.secrets, "prompt_secret")
@mock.patch.object(reset_session_secret.secrets, "read_from_env")
def test_reset_session_secret_run_with_prompts_success(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_confirm,
    mock_set_secret,
    good_secret,
):
    """Test reset_session_secret.run is successful with user input prompts."""
    args = argparse.Namespace()
    args.prompt = True  # require user to confirm
    mock_confirm.return_value = True  # act like use enters 'y'
    mock_set_secret.return_value = True
    mock_prompt_secret.return_value = good_secret

    assert reset_session_secret.run(args)
    mock_read_from_env.assert_not_called()  # because user asked to be prompted
    mock_prompt_secret.assert_called_once()
    mock_set_secret.assert_called_once_with(
        reset_session_secret.SESSION_SECRET_PODMAN_SECRET_NAME, good_secret
    )
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_session_secret.podman_utils, "set_secret")
@mock.patch.object(reset_session_secret.shell_utils, "confirm")
@mock.patch.object(reset_session_secret.secrets, "prompt_secret")
@mock.patch.object(reset_session_secret.secrets, "read_from_env")
def test_reset_session_secret_run_decline_manual_input(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_confirm,
    mock_set_secret,
):
    """Test reset_session_secret.run if user declines manual input confirmation."""
    args = argparse.Namespace()
    args.prompt = True  # require user to confirm
    mock_confirm.return_value = False  # act like use enters 'n'

    assert not reset_session_secret.run(args)
    mock_read_from_env.assert_not_called()  # because user asked to be prompted
    mock_prompt_secret.assert_not_called()
    mock_set_secret.assert_not_called()
    assert len(mock_confirm.call_args_list) == 1


@mock.patch.object(reset_session_secret.podman_utils, "set_secret")
@mock.patch.object(reset_session_secret.shell_utils, "confirm")
@mock.patch.object(reset_session_secret.secrets, "generate_random_secret")
@mock.patch.object(reset_session_secret.secrets, "prompt_secret")
@mock.patch.object(reset_session_secret.secrets, "read_from_env")
def test_reset_session_secret_run_fails_set_secret(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_generate_random_secret,
    mock_confirm,
    mock_set_secret,
    good_secret,
    caplog,
):
    """Test reset_session_secret.run when set_secret fails unexpectedly."""
    caplog.set_level(logging.ERROR)
    args = argparse.Namespace()
    args.prompt = False
    mock_read_from_env.return_value = None, False
    mock_generate_random_secret.return_value = good_secret
    mock_set_secret.return_value = False  # might happen in a race condition

    assert not reset_session_secret.run(args)
    mock_read_from_env.assert_called_once()
    mock_prompt_secret.assert_not_called()  # no prompts for default first-time setup
    mock_confirm.assert_not_called()  # no prompts for default first-time setup
    mock_set_secret.assert_called_once()
    assert "The session secret key was not updated." == caplog.messages[0]


@mock.patch.object(reset_session_secret.podman_utils, "set_secret")
@mock.patch.object(reset_session_secret.shell_utils, "settings")
@mock.patch.object(reset_session_secret.secrets, "prompt_secret")
@mock.patch.object(reset_session_secret.secrets, "read_from_env")
def test_reset_session_secret_run_headless_mode(  # noqa: PLR0913
    mock_read_from_env,
    mock_prompt_secret,
    mock_settings,
    mock_set_secret,
    good_secret,
):
    """Test reset_session_secret.run using env vars, yes, and quiet."""
    args = argparse.Namespace()
    mock_settings.yes = True
    mock_settings.quiet = True
    mock_read_from_env.return_value = good_secret, False
    mock_set_secret.return_value = True

    assert reset_session_secret.run(args)
    mock_read_from_env.assert_called_once()
    mock_prompt_secret.assert_not_called()
    mock_set_secret.assert_called_once_with(
        reset_session_secret.SESSION_SECRET_PODMAN_SECRET_NAME, good_secret
    )
