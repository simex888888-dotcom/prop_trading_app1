"""
pytest configuration for CHM_KRYPTON backend tests.
"""
import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default asyncio policy for all tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
