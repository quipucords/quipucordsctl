"""Package command-line entrypoint."""

import gettext
import importlib.resources as pkg_resources


def set_up_gettext():
    """Set up gettext for string localization."""
    locale_path = pkg_resources.files("quipucordsctl").joinpath("locale")
    gettext.bindtextdomain("messages", localedir=str(locale_path))


def main():
    """Run command-line entrypoint."""
    set_up_gettext()

    # We must run set_up_gettext **before** we import anything else.
    # This helps to guarantee that gettext shared state/globals use
    # our specific bindtextdomain contents.
    from . import cli  # noqa: PLC0415

    cli.run()


if __name__ == "__main__":
    main()
