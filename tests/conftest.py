"""Shared fixtures for pytest tests."""

import pytest


@pytest.fixture
def good_secret(faker):
    """Generate a "good" secret that should pass validation."""
    return faker.password(
        length=128,  # long enough for all intents and purposes
        special_chars=True,
        digits=True,
        upper_case=True,
        lower_case=True,
    )


@pytest.fixture
def bad_secret(faker):
    """Generate a "bad" secret that should fail validation."""
    return faker.password(
        length=4,  # definitely too short
        special_chars=True,
        digits=False,  # should have a number
        upper_case=False,  # should have a letter
        lower_case=False,  # should have a letter
    )
