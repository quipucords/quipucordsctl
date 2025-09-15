"""Basic tests for SystemdUnitParser."""

import pytest

from quipucordsctl.systemdunitparser import SystemdUnitParser

EXAMPLE_CONFIG = """
[hello]
foo=bar
biz=hello
biz=world
port=99999

[other]
"""


@pytest.fixture
def example_config(tmpdir):
    """Create example config files as a test fixture."""
    file_path = tmpdir.join("example.service")
    with file_path.open("w") as fp:
        fp.write(EXAMPLE_CONFIG)
    yield file_path


def test_read(example_config):
    """Test reading a systemd-style config file."""
    parser = SystemdUnitParser()
    parser.read(str(example_config))
    assert parser.sections() == ["hello", "other"]
    assert parser["hello"]["foo"] == "bar"
    assert parser["hello"]["biz"] == ("hello", "world")
    assert parser["hello"]["port"] == "99999"  # always strings
    assert parser["other"] == {}
