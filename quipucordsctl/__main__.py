"""Package command-line entrypoint."""

import gettext
import pathlib


def set_up_gettext():
    """Set up gettext for string localization."""
    locale_dir = pathlib.Path(__file__).parent / "locale"
    gettext.bindtextdomain("messages", str(locale_dir))


if __name__ == "__main__":
    set_up_gettext()

    from .main import main

    main()
