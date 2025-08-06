"""Test the "reset_application_secret" command."""

from unittest import mock

from quipucordsctl.commands import reset_application_secret


def test_application_secret_is_set():
    """Test placeholder for application_secret_is_set."""
    assert not reset_application_secret.application_secret_is_set()


@mock.patch.object(reset_application_secret.shell_utils, "get_podman_client")
@mock.patch.object(reset_application_secret.shell_utils, "confirm")
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
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
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
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
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
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
@mock.patch.object(reset_application_secret.secrets, "prompt_secret")
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
