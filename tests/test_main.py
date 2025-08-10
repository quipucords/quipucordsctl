"""Test the quipucords.__main__ entrypoint module."""

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
