# TOP RAM API Integration

## Overview

This Odoo 18 module extends the Helpdesk application to integrate with the RAM Prime Care API. It automatically notifies an external system whenever a helpdesk ticket's stage changes.

## Features

- **Workflow Level Field**: Adds a new `workflow_level` field (1-10) to helpdesk tickets
- **Automatic API Calls**: Triggers API calls when ticket stage changes
- **Bearer Token Authentication**: Secure API authentication with dynamic token configuration
- **Toast Notifications**: Real-time visual feedback with success/warning/error notifications
- **Dynamic Configuration**: Configure token and endpoint through UI (no code changes needed)
- **Error Handling**: Robust error handling and logging for API failures
- **Non-Blocking**: API failures don't prevent ticket updates

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "TOP RAM API Integration" module
4. (Optional) Configure Bearer token: Helpdesk → Configuration → Settings → RAM Prime Care API Integration

## Dependencies

- `helpdesk` - Odoo Helpdesk module

## API Integration

When a ticket's stage changes, the module calls:

```
https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/{ticketId}/{workFlowLevel}/{status}/{updateTime}
```

### Parameters

- **ticketId**: Ticket name/number
- **workFlowLevel**: Selected workflow level (1-10)
- **status**: New stage name
- **updateTime**: Timestamp of the update (format: YYYY-MM-DD_HH:MM:SS)

### Authentication

The module sends a Bearer token for authentication:

```http
Authorization: Bearer eyJraWQiOiJqd3QudGVjaG5hcy5rZXkiLC...
```

**Configure Token**: Helpdesk → Configuration → Settings → RAM Prime Care API Integration

See [BEARER_TOKEN_SETUP.md](BEARER_TOKEN_SETUP.md) for detailed configuration instructions.

### Example API Call

```
https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/TICKET-001/3/In%20Progress/2025-10-09_14:30:45
```

## Configuration

### Changing API Endpoint

To modify the API endpoint, edit `models/helpdesk_ticket.py`:

```python
base_url = 'https://your-new-api-endpoint.com/path'
```

### Changing Request Method

The module uses GET requests by default. To use POST:

```python
response = requests.post(api_url, json=data, timeout=10)
```

### Timeout Configuration

Default timeout is 10 seconds. Adjust in `_call_ram_api`:

```python
response = requests.get(api_url, timeout=30)  # 30 seconds
```

## Usage

1. Open a helpdesk ticket
2. Set the **Workflow Level** (1-10)
3. Change the ticket's **Stage**
4. The API is automatically called with the ticket information
5. A **toast notification** appears showing the sync status:
   - ✅ **Green** = Success (HTTP 200)
   - ⚠️ **Orange** = Warning (non-200 status)
   - 🚫 **Red** = Error (timeout/connection failure)

## Logging & Notifications

### Toast Notifications

Users receive real-time visual feedback:

- **Success** (Green): "Ticket XXX successfully synced with RAM Prime Care API"
- **Warning** (Orange): "Ticket XXX synced but API returned status XXX"
- **Error** (Red): "Failed to sync ticket XXX: [error details]"

Notifications auto-dismiss after a few seconds. See [TOAST_NOTIFICATIONS.md](TOAST_NOTIFICATIONS.md) for details.

### System Logs

The module also logs all API interactions:

- **Info**: Successful API calls
- **Warning**: API calls that return non-200 status
- **Error**: Failed API calls (timeout, connection errors)

Check logs in Odoo's logging system or log files.

## Troubleshooting

### API Calls Not Working

1. Check Odoo logs for error messages
2. Verify the `requests` library is installed: `pip install requests`
3. Ensure network connectivity to ramprimecare.com
4. Check firewall settings

### Field Not Showing

1. Verify module installation
2. Update the app (Apps → TOP RAM API Integration → Upgrade)
3. Clear browser cache

## Technical Details

### Model Extension

```python
_inherit = 'helpdesk.ticket'
```

### Key Methods

- `write()`: Detects stage changes and triggers API calls
- `_call_ram_api()`: Handles the HTTP request to external API

### Field Definition

```python
workflow_level = fields.Selection(
    selection=[('1', 'Level 1'), ..., ('10', 'Level 10')],
    default='1',
    required=True
)
```

## License

LGPL-3

## Support

For issues or questions, contact your development team.

