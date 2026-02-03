# Slack Processor

**Send Slack notifications based on Doover events**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[Getting Started](#getting-started) | [Configuration](#configuration) | [Triggers](#triggers) | [Development](#development)

## Overview

A Doover processor that sends Slack notifications based on configurable triggers:

- **Channel Alerts**: Notify when subscribed channels receive messages
- **Offline Alerts**: Notify when devices go offline or stay offline
- **Threshold Alerts**: Notify when tag values exceed configured limits

## Getting Started

### Prerequisites

1. A Slack workspace with an incoming webhook configured
2. Access to the Doover admin portal

### Creating a Slack Webhook

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app or select an existing one
3. Enable "Incoming Webhooks"
4. Add a new webhook to your workspace
5. Copy the webhook URL

### Installation

Install the processor on a device through the Doover admin portal and configure the required settings.

## Configuration

### Required Settings

| Setting | Description |
|---------|-------------|
| **Channel Subscriptions** | List of channels to monitor for message alerts |
| **Schedule** | How often to run offline and threshold checks (e.g., `rate(5 minutes)`) |
| **Slack Webhook URL** | The incoming webhook URL from Slack |

### Slack Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Slack Channel Override** | Override the default webhook channel | _(webhook default)_ |
| **Slack Bot Username** | Display name for the bot in Slack | `Doover Alerts` |

### Channel Alert Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Enable Channel Alerts** | Send notifications on channel messages | `true` |
| **Channel Message Template** | Message template with `{channel}`, `{data}`, `{device}` placeholders | See below |

Default template: `New message on {channel} from {device}: {data}`

### Offline Alert Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Enable Offline Alerts** | Send notifications when devices go offline | `false` |
| **Offline Threshold (minutes)** | How long before alerting (1-1440) | `30` |
| **Offline Reminder Interval (minutes)** | How often to remind while offline (0 to disable) | `60` |

### Threshold Alert Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Enable Threshold Alerts** | Send notifications on threshold breaches | `false` |
| **Tag Thresholds** | Array of threshold configurations | `[]` |

Each threshold configuration includes:

| Field | Description |
|-------|-------------|
| **Tag Name** | The tag to monitor |
| **Upper Limit** | Alert when value exceeds this |
| **Lower Limit** | Alert when value falls below this |
| **Alert Message** | Custom message with `{tag}`, `{value}`, `{limit}`, `{device}` placeholders |
| **Cooldown Minutes** | Minimum time between repeated alerts |

## Triggers

### Channel Messages (`on_message_create`)

When a subscribed channel receives a message, the processor sends a Slack notification with the channel name, message data, and device name.

### Scheduled Checks (`on_schedule`)

On each scheduled run, the processor:

1. **Offline Check**: Queries the device connection status and alerts if offline longer than the threshold
2. **Threshold Check**: Reads tag values and alerts if any exceed configured limits

## Tags

The processor tracks statistics via tags:

| Tag | Description |
|-----|-------------|
| `channel_alerts_sent` | Count of channel message alerts sent |
| `offline_alerts_sent` | Count of offline alerts sent |
| `threshold_alerts_sent` | Count of threshold alerts sent |
| `last_error` | Last error message (if any) |
| `last_error_at` | Timestamp of last error |

## Development

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd slack-processor

# Install dependencies
uv sync
```

### Building

```bash
# Build the deployment package
./build.sh
```

This creates `package.zip` for deployment.

### Testing

```bash
uv run pytest
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
