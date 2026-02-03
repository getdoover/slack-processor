from typing import Any

from pydoover.cloud.processor import run_app

from .application import SlackProcessor
from .app_config import SlackProcessorConfig


def handler(event: dict[str, Any], context):
    """
    Lambda handler entry point for the Slack Processor.
    """
    SlackProcessorConfig.clear_elements()
    run_app(
        SlackProcessor(config=SlackProcessorConfig()),
        event,
        context,
    )
