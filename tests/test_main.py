"""Test the quipucords.__main__ entrypoint module."""

import sys
from unittest import mock

from quipucordsctl import __main__


@mock.patch.object(__main__, "gettext")
@mock.patch.object(__main__, "pkg_resources")
def test_set_up_gettext(mock_pkg_resources, mock_gettext):
    """Test set_up_gettext expected behavior."""
    base_path = mock_pkg_resources.files.return_value
    locale_path = mock.Mock()
    base_path.joinpath.return_value = locale_path

    __main__.set_up_gettext()

    base_path.joinpath.assert_called_once_with("locale")
    mock_gettext.bindtextdomain.assert_called_once_with(
        "messages", localedir=str(locale_path)
    )


def test_main_invokes_other_setup_and_cli_run(mocker):
    """Test the main entrypoint function."""
    # Important note! We must locally reimport __main__ inside this test
    # function to avoid a situation where other tests may have already
    # imported quipucordsctl.cli, which would then persist in Python's
    # internal imported modules cache which is difficult to patch.
    import quipucordsctl.__main__ as main_module  # noqa: PLC0415

    mock_other_setup = mocker.patch.object(main_module, "set_up_gettext")
    mock_run = mocker.patch("quipucordsctl.cli.run")

    main_module.main()

    mock_other_setup.assert_called_once_with()
    mock_run.assert_called_once_with()


def test_main_invokes_pip_install_podman(mocker):
    """Tests the main entrypoint on RPM-based installations installs podman."""
    import quipucordsctl.__main__ as main_module  # noqa: PLC0415
    import quipucordsctl.shell_utils as shell_utils_module  # noqa: PLC0415

    mock_setup_gettext = mocker.patch.object(main_module, "set_up_gettext")
    mock_is_rpm_exec = mocker.patch.object(shell_utils_module, "is_rpm_exec")
    mock_run_command = mocker.patch.object(shell_utils_module, "run_command")
    mock_run = mocker.patch("quipucordsctl.cli.run")

    mock_is_rpm_exec.return_value = True

    main_module.main()

    mock_setup_gettext.assert_called_once_with()
    mock_run_command.assert_has_calls(
        [
            mock.call([sys.executable, "-m", "ensurepip"]),
            mock.call([sys.executable, "-m", "pip", "-q", "install", "podman"]),
        ]
    )
    mock_run.assert_called_once_with()
