from pathlib import Path

from pydoover import config
from pydoover.cloud.processor import ManySubscriptionConfig, ScheduleConfig


class SlackProcessorConfig(config.Schema):
    """
    Configuration schema for Slack Processor.

    This processor can send Slack notifications based on:
    - Channel messages (when subscribed channels receive data)
    - Device offline status (when devices go offline or stay offline)
    - Tag threshold breaches (when tag values exceed configured limits)
    """

    def __init__(self):
        # Channel subscriptions - triggers on_message_create
        self.subscription = ManySubscriptionConfig()

        # Schedule - for periodic checks (offline monitoring, threshold checks)
        self.schedule = ScheduleConfig()

        # Slack Configuration
        self.slack_webhook_url = config.String(
            "Slack Webhook URL",
            description="The Slack incoming webhook URL for sending messages",
        )

        self.slack_channel = config.String(
            "Slack Channel Override",
            description="Optional: Override the default webhook channel (e.g., #alerts)",
            default="",
        )

        self.slack_username = config.String(
            "Slack Bot Username",
            description="Display name for the bot in Slack",
            default="Doover Alerts",
        )

        # Channel Message Alerts Configuration
        self.channel_alerts_enabled = config.Boolean(
            "Enable Channel Alerts",
            description="Send Slack notifications when subscribed channels receive messages",
            default=True,
        )

        self.channel_message_template = config.String(
            "Channel Message Template",
            description="Message template for channel alerts. Use {channel}, {data}, {device} placeholders",
            default="New message on {channel} from {device}: {data}",
        )

        # Offline Monitoring Configuration
        self.offline_alerts_enabled = config.Boolean(
            "Enable Offline Alerts",
            description="Send Slack notifications when devices go offline",
            default=False,
        )

        self.offline_threshold_minutes = config.Integer(
            "Offline Threshold (minutes)",
            description="Minutes before a device is considered offline and alert is sent",
            default=30,
            minimum=1,
            maximum=1440,
        )

        self.offline_reminder_interval_minutes = config.Integer(
            "Offline Reminder Interval (minutes)",
            description="How often to send reminders while device stays offline (0 to disable)",
            default=60,
            minimum=0,
            maximum=1440,
        )

        # Tag Threshold Alerts Configuration
        self.threshold_alerts_enabled = config.Boolean(
            "Enable Threshold Alerts",
            description="Send Slack notifications when tag values exceed thresholds",
            default=False,
        )

        self.tag_thresholds = config.Array(
            "Tag Thresholds",
            element=config.Object("Threshold"),
            description="Configure tag thresholds that trigger alerts",
        )
        self.tag_thresholds.element.add_elements(
            config.String(
                "Tag Name",
                description="The name of the tag to monitor",
            ),
            config.Number(
                "Upper Limit",
                description="Alert when tag value exceeds this (leave empty to disable)",
            ),
            config.Number(
                "Lower Limit",
                description="Alert when tag value falls below this (leave empty to disable)",
            ),
            config.String(
                "Alert Message",
                description="Custom alert message. Use {tag}, {value}, {limit}, {device} placeholders",
                default="{tag} is {value} (threshold: {limit}) on {device}",
            ),
            config.Integer(
                "Cooldown Minutes",
                description="Minimum time between repeated alerts for this threshold",
                default=15,
            ),
        )

        # General Settings
        self.include_device_name = config.Boolean(
            "Include Device Name",
            description="Include the device name in Slack messages",
            default=True,
        )

        self.request_timeout_seconds = config.Integer(
            "Request Timeout (seconds)",
            description="HTTP request timeout for Slack API calls",
            default=30,
            minimum=5,
            maximum=120,
        )


def export():
    SlackProcessorConfig().export(
        Path(__file__).parents[2] / "doover_config.json", "slack_processor"
    )


if __name__ == "__main__":
    export()
