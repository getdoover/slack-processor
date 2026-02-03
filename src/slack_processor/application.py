import json
import logging
from datetime import datetime, timezone, timedelta

import requests

from pydoover.cloud.processor import (
    Application,
    MessageCreateEvent,
)
from pydoover.cloud.processor.types import ScheduleEvent

from .app_config import SlackProcessorConfig

log = logging.getLogger(__name__)


class SlackProcessor(Application):
    """
    Doover Processor that sends Slack notifications based on configurable triggers.

    Supported triggers:
    - Channel messages: Sends alerts when subscribed channels receive messages
    - Device offline: Monitors connection status and alerts when devices go offline
    - Tag thresholds: Monitors tag values and alerts when thresholds are exceeded
    """

    config: SlackProcessorConfig

    async def setup(self):
        """Called once per invocation before event processing."""
        log.info("Slack processor initializing")

    async def close(self):
        """Called once per invocation after event processing."""
        log.info("Slack processor closing")

    async def on_message_create(self, event: MessageCreateEvent):
        """React to channel messages - send Slack notification if configured."""
        log.info(f"Received message on channel: {event.channel_name}")

        if not self.config.channel_alerts_enabled.value:
            log.debug("Channel alerts disabled, skipping")
            return

        webhook_url = self.config.slack_webhook_url.value
        if not webhook_url:
            log.warning("Slack webhook URL not configured, skipping alert")
            return

        # Get device name if available
        device_name = await self._get_device_name()

        # Format the message data
        data = event.message.data
        if isinstance(data, dict):
            data_str = json.dumps(data, indent=2, default=str)
        else:
            data_str = str(data)

        # Build message from template
        template = self.config.channel_message_template.value
        message = template.format(
            channel=event.channel_name,
            data=data_str,
            device=device_name,
        )

        # Send to Slack
        await self._send_slack_message(
            text=message,
            title=f"Channel Alert: {event.channel_name}",
            color="#36a64f",  # green
        )

        # Update stats
        await self._increment_stat("channel_alerts_sent")

    async def on_schedule(self, event: ScheduleEvent):
        """Run periodic checks - offline monitoring and threshold checks."""
        log.info("Running scheduled checks")

        webhook_url = self.config.slack_webhook_url.value
        if not webhook_url:
            log.warning("Slack webhook URL not configured, skipping scheduled checks")
            return

        # Check offline status
        if self.config.offline_alerts_enabled.value:
            await self._check_offline_status()

        # Check tag thresholds
        if self.config.threshold_alerts_enabled.value:
            await self._check_tag_thresholds()

    async def _check_offline_status(self):
        """Check if device is offline and send alert if needed."""
        log.info("Checking device offline status")

        # Get connection info from the device
        try:
            connection_info = await self.api.get_agent_connection(self.agent_id)
            last_online = connection_info.get("online_at")
            is_online = connection_info.get("determination") == "online"
        except Exception as e:
            log.warning(f"Could not get connection info: {e}")
            return

        if is_online:
            # Device is online, clear any offline tracking
            await self.set_tag("offline_alert_sent", False)
            await self.set_tag("last_offline_reminder", None)
            return

        # Device is offline - check threshold
        threshold_minutes = self.config.offline_threshold_minutes.value
        if last_online:
            if isinstance(last_online, str):
                last_online_dt = datetime.fromisoformat(last_online.replace("Z", "+00:00"))
            else:
                last_online_dt = datetime.fromtimestamp(last_online, timezone.utc)

            offline_duration = datetime.now(timezone.utc) - last_online_dt
            offline_minutes = offline_duration.total_seconds() / 60

            if offline_minutes < threshold_minutes:
                log.debug(f"Device offline for {offline_minutes:.1f} min, threshold is {threshold_minutes} min")
                return

        # Check if we already sent an alert
        alert_sent = await self.get_tag("offline_alert_sent", False)
        last_reminder = await self.get_tag("last_offline_reminder")

        device_name = await self._get_device_name()
        reminder_interval = self.config.offline_reminder_interval_minutes.value

        should_send = False
        if not alert_sent:
            should_send = True
            message = f"Device *{device_name}* has gone offline"
        elif reminder_interval > 0 and last_reminder:
            # Check if we should send a reminder
            if isinstance(last_reminder, str):
                last_reminder_dt = datetime.fromisoformat(last_reminder.replace("Z", "+00:00"))
            else:
                last_reminder_dt = datetime.fromtimestamp(last_reminder, timezone.utc)

            since_reminder = datetime.now(timezone.utc) - last_reminder_dt
            if since_reminder.total_seconds() / 60 >= reminder_interval:
                should_send = True
                offline_mins = int(offline_duration.total_seconds() / 60) if last_online else "unknown"
                message = f"Device *{device_name}* is still offline (duration: {offline_mins} minutes)"

        if should_send:
            await self._send_slack_message(
                text=message,
                title="Device Offline Alert",
                color="#ff0000",  # red
            )
            await self.set_tag("offline_alert_sent", True)
            await self.set_tag("last_offline_reminder", datetime.now(timezone.utc).isoformat())
            await self._increment_stat("offline_alerts_sent")

    async def _check_tag_thresholds(self):
        """Check configured tag thresholds and send alerts if exceeded."""
        log.info("Checking tag thresholds")

        thresholds = self.config.tag_thresholds.value or []
        if not thresholds:
            log.debug("No tag thresholds configured")
            return

        # Get current tag values
        try:
            tag_values_channel = self.fetch_channel_named("tag_values")
            tag_values = tag_values_channel.get_aggregate() or {}
        except Exception as e:
            log.warning(f"Could not fetch tag_values channel: {e}")
            return

        device_name = await self._get_device_name()
        now = datetime.now(timezone.utc)

        for threshold_config in thresholds:
            tag_name = threshold_config.get("tag_name")
            if not tag_name:
                continue

            value = tag_values.get(tag_name)
            if value is None:
                log.debug(f"Tag {tag_name} not found")
                continue

            try:
                value = float(value)
            except (TypeError, ValueError):
                log.debug(f"Tag {tag_name} value {value} is not numeric")
                continue

            upper_limit = threshold_config.get("upper_limit")
            lower_limit = threshold_config.get("lower_limit")
            message_template = threshold_config.get("alert_message", "{tag} is {value} (threshold: {limit}) on {device}")
            cooldown_minutes = threshold_config.get("cooldown_minutes", 15)

            # Check if we should alert (cooldown)
            cooldown_key = f"threshold_cooldown_{tag_name}"
            last_alert = await self.get_tag(cooldown_key)
            if last_alert:
                if isinstance(last_alert, str):
                    last_alert_dt = datetime.fromisoformat(last_alert.replace("Z", "+00:00"))
                else:
                    last_alert_dt = datetime.fromtimestamp(last_alert, timezone.utc)

                if (now - last_alert_dt).total_seconds() / 60 < cooldown_minutes:
                    log.debug(f"Tag {tag_name} in cooldown period")
                    continue

            # Check upper limit
            if upper_limit is not None and value > upper_limit:
                message = message_template.format(
                    tag=tag_name,
                    value=value,
                    limit=f">{upper_limit}",
                    device=device_name,
                )
                await self._send_slack_message(
                    text=message,
                    title="Threshold Alert: High Value",
                    color="#ff9900",  # orange
                )
                await self.set_tag(cooldown_key, now.isoformat())
                await self._increment_stat("threshold_alerts_sent")
                continue  # Don't check lower limit if upper triggered

            # Check lower limit
            if lower_limit is not None and value < lower_limit:
                message = message_template.format(
                    tag=tag_name,
                    value=value,
                    limit=f"<{lower_limit}",
                    device=device_name,
                )
                await self._send_slack_message(
                    text=message,
                    title="Threshold Alert: Low Value",
                    color="#0066ff",  # blue
                )
                await self.set_tag(cooldown_key, now.isoformat())
                await self._increment_stat("threshold_alerts_sent")

    async def _send_slack_message(self, text: str, title: str = None, color: str = "#36a64f"):
        """Send a message to Slack via webhook."""
        webhook_url = self.config.slack_webhook_url.value
        if not webhook_url:
            log.error("No Slack webhook URL configured")
            return

        # Build the payload
        payload = {
            "username": self.config.slack_username.value or "Doover Alerts",
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": text,
                    "footer": "Doover Slack Processor",
                    "ts": int(datetime.now(timezone.utc).timestamp()),
                }
            ],
        }

        # Add channel override if configured
        channel = self.config.slack_channel.value
        if channel:
            payload["channel"] = channel

        # Send to Slack
        timeout = self.config.request_timeout_seconds.value or 30
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )

            if response.status_code == 200:
                log.info(f"Slack message sent successfully: {title}")
            else:
                log.error(f"Slack API error: {response.status_code} - {response.text}")
                await self._update_error(f"Slack API error: {response.status_code}")

        except requests.exceptions.Timeout:
            log.error(f"Slack request timed out after {timeout}s")
            await self._update_error("Slack request timeout")
        except requests.exceptions.RequestException as e:
            log.error(f"Slack request failed: {e}")
            await self._update_error(f"Slack request failed: {e}")

    async def _get_device_name(self) -> str:
        """Get the device name for inclusion in messages."""
        if not self.config.include_device_name.value:
            return "Unknown Device"

        try:
            # Try to get device name from agent info
            agent_info = await self.api.get_agent(self.agent_id)
            return agent_info.get("name", agent_info.get("display_name", str(self.agent_id)))
        except Exception as e:
            log.debug(f"Could not get device name: {e}")
            return str(self.agent_id)

    async def _increment_stat(self, stat_name: str):
        """Increment a statistics counter."""
        try:
            current = await self.get_tag(stat_name, 0)
            await self.set_tag(stat_name, current + 1)
            await self.set_tag(f"{stat_name}_last", datetime.now(timezone.utc).isoformat())
        except Exception as e:
            log.warning(f"Could not update stat {stat_name}: {e}")

    async def _update_error(self, error: str):
        """Record the last error."""
        try:
            await self.set_tag("last_error", error)
            await self.set_tag("last_error_at", datetime.now(timezone.utc).isoformat())
        except Exception as e:
            log.warning(f"Could not update error tag: {e}")
