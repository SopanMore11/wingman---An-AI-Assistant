"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_message():
    """Provide a sample message for testing."""
    return "Hello, Wingman!"


@pytest.fixture
def sample_user_id():
    """Provide a sample user ID for testing."""
    return "user_12345"


@pytest.fixture
def sample_session_id():
    """Provide a sample session ID for testing."""
    return "session_12345"
