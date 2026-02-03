"""
Basic tests for the Slack Processor.

This ensures all modules are importable and that the config is valid.
"""


def test_import_app():
    from slack_processor.application import SlackProcessor

    assert SlackProcessor


def test_config():
    from slack_processor.app_config import SlackProcessorConfig

    config = SlackProcessorConfig()
    assert isinstance(config.to_dict(), dict)


def test_handler():
    from slack_processor import handler

    assert callable(handler)
