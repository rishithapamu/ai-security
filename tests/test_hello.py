"""Smoke tests — Day 1 DoD: CI must be green on this."""

from src import hello


def test_hello_returns_string() -> None:
    result = hello()
    assert isinstance(result, str)


def test_hello_content() -> None:
    assert "ai-sec-workbench" in hello()
