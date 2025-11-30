"""Test the quipucordsctl.secrets module."""

import dataclasses
import logging
from unittest import mock

import pytest

from quipucordsctl import secrets


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
    assert secrets.check_secret(new_secret, **kwargs) == expected_result


@mock.patch.object(secrets.getpass, "getpass")
def test_prompt_secret_success(mock_getpass, good_secret, caplog):
    """Test prompt_secret succeeds with successful input."""
    caplog.set_level(logging.ERROR)
    mock_getpass.side_effect = [good_secret, good_secret]
    messages = mock.Mock()

    assert secrets.prompt_secret(messages) == good_secret
    mock_getpass.assert_has_calls(
        [
            mock.call(messages.prompt_enter_value),
            mock.call(messages.prompt_confirm_value),
        ]
    )
    assert len(caplog.messages) == 0


@mock.patch.object(secrets.getpass, "getpass")
def test_prompt_secret_fails_mismatch(mock_getpass, good_secret, bad_secret, caplog):
    """Test prompt_secret fails when inputs don't match."""
    caplog.set_level(logging.ERROR)
    mock_getpass.side_effect = [good_secret, good_secret[::-1]]

    messages = secrets.ResetSecretMessages()
    assert not secrets.prompt_secret()
    assert len(caplog.messages) == 1
    assert str(messages.prompt_values_no_match) in caplog.messages


@dataclasses.dataclass
class GetNewSecretValueTestCase:
    """Define expectations and simulated inputs to test get_new_secret_value."""

    expect_success: bool
    already_exists: bool = False
    must_confirm_replace_existing: bool = False
    must_confirm_allow_nonrandom: bool = False
    must_prompt_interactive_input: bool = False
    may_prompt_interactive_input: bool = False
    simulate_allow_replace_existing: bool = False
    simulate_allow_nonrandom: bool = False
    simulate_quiet_mode: bool = False
    simulate_yes_mode: bool = False
    simulate_invalid_input: bool = False
    simulate_env_var_set: bool = False
    simulate_invalid_env_var: bool = False
    expect_random: bool = False


get_new_secret_value_test_cases = {
    "random-basic": GetNewSecretValueTestCase(
        # like "reset_session_secret" first time behavior
        expect_random=True,
        expect_success=True,
    ),
    "random-exists-allow": GetNewSecretValueTestCase(
        # like "reset_session_secret" after already run, then 'y'
        must_confirm_replace_existing=True,
        simulate_allow_replace_existing=True,
        expect_random=True,
        expect_success=True,
    ),
    "random-exists-decline": GetNewSecretValueTestCase(
        # like "reset_session_secret" after already run, then 'n'
        must_confirm_replace_existing=True,
        simulate_allow_replace_existing=False,
        expect_random=True,
        expect_success=False,
    ),
    "interactive": GetNewSecretValueTestCase(
        # like "reset_admin_password" first time behavior
        may_prompt_interactive_input=True,
        expect_success=True,
    ),
    "interactive-invalid": GetNewSecretValueTestCase(
        # like "reset_admin_password" failure
        may_prompt_interactive_input=True,
        simulate_invalid_input=True,
        expect_success=False,
    ),
    "interactive-confirm-nonrandom-allow": GetNewSecretValueTestCase(
        # like "reset_database_password --prompt" first time, "y"
        must_prompt_interactive_input=True,
        must_confirm_allow_nonrandom=True,
        simulate_allow_nonrandom=True,
        expect_success=True,
    ),
    "interactive-confirm-nonrandom-decline": GetNewSecretValueTestCase(
        # like "reset_database_password --prompt" first time, "y"
        must_prompt_interactive_input=True,
        must_confirm_allow_nonrandom=True,
        simulate_allow_nonrandom=False,
        expect_success=False,
    ),
    "interactive-exists-confirm-nonrandom-allow-decline": GetNewSecretValueTestCase(
        # like "reset_database_password --prompt" after already run, "y", "n"
        must_confirm_replace_existing=True,
        must_prompt_interactive_input=True,
        must_confirm_allow_nonrandom=True,
        simulate_allow_replace_existing=False,
        simulate_allow_nonrandom=False,
        expect_success=False,
    ),
    "interactive-confirm-yes-mode": GetNewSecretValueTestCase(
        # like "-y reset_database_password --prompt" after already run
        must_prompt_interactive_input=True,
        must_confirm_allow_nonrandom=True,
        simulate_yes_mode=True,
        expect_success=True,
    ),
    "env-var-headless": GetNewSecretValueTestCase(
        # like "-y -q reset_database_password" with env var first time behavior
        simulate_env_var_set=True,
        simulate_yes_mode=True,
        simulate_quiet_mode=True,
        expect_success=True,
    ),
    "env-var-headless-exists-yes": GetNewSecretValueTestCase(
        # like "-y -q reset_database_password" with env var after already run
        simulate_env_var_set=True,
        must_confirm_replace_existing=True,
        simulate_yes_mode=True,
        simulate_quiet_mode=True,
        expect_success=True,
    ),
    "env-var-headless-exists-abort": GetNewSecretValueTestCase(
        # like "-q reset_database_password" with env var after already run
        simulate_env_var_set=True,
        must_confirm_replace_existing=True,
        simulate_quiet_mode=True,
        expect_random=False,
        expect_success=False,
    ),
}


@pytest.mark.parametrize("name,test_case", get_new_secret_value_test_cases.items())
def test_get_new_secret_value(
    name: str, test_case: GetNewSecretValueTestCase, faker, mocker
):
    """Test `get_new_secret` behaviors under different conditions and user inputs."""
    podman_secret_name = faker.slug()
    input_value = faker.password()

    secrets_runtime = mocker.patch.object(secrets.settings, "runtime")
    shell_utils_runtime = mocker.patch.object(secrets.shell_utils.settings, "runtime")
    secrets_runtime.quiet = shell_utils_runtime.quiet = test_case.simulate_quiet_mode
    secrets_runtime.yes = shell_utils_runtime.yes = test_case.simulate_yes_mode

    if not test_case.simulate_quiet_mode and not test_case.simulate_yes_mode:
        mocker.patch.object(
            secrets,
            "confirm_replace_existing",
            return_value=test_case.simulate_allow_replace_existing,
        )
        mocker.patch.object(
            secrets,
            "confirm_allow_nonrandom",
            return_value=test_case.simulate_allow_nonrandom,
        )

    if not test_case.simulate_quiet_mode:
        mocker.patch.object(secrets.getpass, "getpass", return_value=input_value)

    if test_case.simulate_env_var_set:
        mock_get_env = mocker.patch.object(secrets.shell_utils, "get_env")
        mock_get_env.return_value = input_value

    env_var_name = faker.slug() if test_case.simulate_env_var_set else None

    mocker.patch.object(
        secrets,
        "check_secret",
        return_value=None if test_case.simulate_invalid_input else input_value,
    )
    if test_case.expect_random:
        mocker.patch.object(secrets, "generate_random_secret", return_value=input_value)

    result = secrets.get_new_secret_value(
        podman_secret_name,
        env_var_name=env_var_name,
        check_requirements={},
        must_confirm_replace_existing=test_case.must_confirm_replace_existing,
        must_confirm_allow_nonrandom=test_case.must_confirm_allow_nonrandom,
        may_prompt_interactive_input=test_case.may_prompt_interactive_input,
        must_prompt_interactive_input=test_case.must_prompt_interactive_input,
    )
    if test_case.expect_success:
        assert result == input_value
    else:
        assert result is None


@mock.patch("builtins.input")
def test_prompt_username_success(mock_input):
    """Test prompt_username returns user input."""
    test_username = "new-admin-username"
    mock_input.return_value = test_username
    messages = mock.Mock()

    assert secrets.prompt_username(messages) == test_username
    mock_input.assert_called_once_with(messages.prompt_enter_value)


def test_reset_username_success(mocker, caplog):
    """Test reset_username succeeds with valid username."""
    caplog.set_level(logging.DEBUG)
    test_username = "new-admin-username"
    podman_secret_name = "quipucords-server-username"

    mocker.patch.object(secrets.podman_utils, "secret_exists", return_value=False)
    mocker.patch.object(secrets, "get_new_username_value", return_value=test_username)
    mock_set_secret = mocker.patch.object(
        secrets.podman_utils, "set_secret", return_value=True
    )

    result = secrets.reset_username(podman_secret_name)

    assert result is True
    mock_set_secret.assert_called_once_with(podman_secret_name, test_username, False)


def test_reset_username_fails_when_no_username_provided(mocker, caplog):
    """Test reset_username fails when get_new_username_value returns None."""
    caplog.set_level(logging.ERROR)
    podman_secret_name = "quipucords-server-username"

    mocker.patch.object(secrets.podman_utils, "secret_exists", return_value=False)
    mocker.patch.object(secrets, "get_new_username_value", return_value=None)
    mock_set_secret = mocker.patch.object(secrets.podman_utils, "set_secret")

    result = secrets.reset_username(podman_secret_name)

    assert result is False
    mock_set_secret.assert_not_called()


def test_reset_username_replaces_existing_secret(mocker, caplog):
    """Test reset_username replaces existing secret when confirmed."""
    caplog.set_level(logging.DEBUG)
    test_username = "replaceduser"
    podman_secret_name = "quipucords-server-username"

    mocker.patch.object(secrets.podman_utils, "secret_exists", return_value=True)
    mocker.patch.object(secrets, "get_new_username_value", return_value=test_username)
    mock_set_secret = mocker.patch.object(
        secrets.podman_utils, "set_secret", return_value=True
    )

    result = secrets.reset_username(podman_secret_name)

    assert result is True
    # already_exists=True should be passed to set_secret
    mock_set_secret.assert_called_once_with(podman_secret_name, test_username, True)


def test_reset_username_confirms_before_replacing(mocker, caplog):
    """Test reset_username passes must_confirm_replace_existing."""
    caplog.set_level(logging.DEBUG)
    test_username = "confirmeduser"
    podman_secret_name = "quipucords-server-username"

    mocker.patch.object(secrets.podman_utils, "secret_exists", return_value=True)
    mock_get_new_username = mocker.patch.object(
        secrets, "get_new_username_value", return_value=test_username
    )
    mocker.patch.object(secrets.podman_utils, "set_secret", return_value=True)

    result = secrets.reset_username(
        podman_secret_name, must_confirm_replace_existing=True
    )

    assert result is True
    call_kwargs = mock_get_new_username.call_args.kwargs
    assert call_kwargs.get("must_confirm_replace_existing") is True
