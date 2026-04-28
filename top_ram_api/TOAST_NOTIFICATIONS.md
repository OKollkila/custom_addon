# Toast Notification Feature

## Overview

The module now includes **real-time toast notifications** that appear when the API sync happens. Users get instant visual feedback about the status of each API call.

## Notification Types

### ✅ Success Notification (Green)
**Appears when:** API call returns HTTP 200 status

**Message:** 
```
🟢 API Sync Success
Ticket TICKET-XXX successfully synced with RAM Prime Care API
```

**Auto-dismisses:** After 4 seconds

---

### ⚠️ Warning Notification (Orange)
**Appears when:** API call completes but returns non-200 status (e.g., 404, 500)

**Message:**
```
🟡 API Sync Warning
Ticket TICKET-XXX synced but API returned status 404
```

**Auto-dismisses:** After 6 seconds

---

### 🚫 Error Notification (Red)
**Appears when:** API call fails (timeout, network error, connection refused)

**Message:**
```
🔴 API Sync Failed
Failed to sync ticket TICKET-XXX with RAM Prime Care API: Connection timeout
```

**Auto-dismisses:** After 8 seconds

---

## How It Works

### User Experience Flow

1. **User opens a helpdesk ticket**
   ```
   Ticket: TICKET-001
   Stage: New
   Workflow Level: 3
   ```

2. **User changes the stage**
   ```
   New → In Progress
   ```

3. **Toast notification appears immediately**
   ```
   ┌─────────────────────────────────────────────┐
   │ ✅ API Sync Success                         │
   │ Ticket TICKET-001 successfully synced       │
   │ with RAM Prime Care API                     │
   └─────────────────────────────────────────────┘
   ```

4. **Notification auto-dismisses**
   - Success: 4 seconds
   - Warning: 6 seconds
   - Error: 8 seconds (gives user time to read error)

---

## Technical Implementation

### Method: `_show_notification()`

Located in `models/helpdesk_ticket.py`:

```python
def _show_notification(self, title, message, notification_type='info'):
    """
    Display toast notification to the user.
    
    :param title: Notification title
    :param message: Notification message
    :param notification_type: success, warning, danger, info
    """
    self.ensure_one()
    
    # Send notification via Odoo bus system
    self.env['bus.bus']._sendone(
        self.env.user.partner_id,
        'simple_notification',
        {
            'title': title,
            'message': message,
            'type': notification_type,
            'sticky': False,  # Auto-dismiss
        }
    )
```

### Notification Triggers

#### Success (HTTP 200)
```python
if response.status_code == 200:
    ticket._show_notification(
        _('API Sync Success'),
        _('Ticket %s successfully synced with RAM Prime Care API') % ticket.name,
        'success'
    )
```

#### Warning (Non-200 status)
```python
elif response:
    ticket._show_notification(
        _('API Sync Warning'),
        _('Ticket %s synced but API returned status %s') % (ticket.name, response.status_code),
        'warning'
    )
```

#### Error (Exception)
```python
except Exception as e:
    ticket._show_notification(
        _('API Sync Failed'),
        _('Failed to sync ticket %s: %s') % (ticket.name, str(e)),
        'danger'
    )
```

---

## Customization

### Change Auto-Dismiss Duration

The notifications auto-dismiss by default. To make them sticky (require manual dismiss):

```python
self.env['bus.bus']._sendone(
    self.env.user.partner_id,
    'simple_notification',
    {
        'title': title,
        'message': message,
        'type': odoo_type,
        'sticky': True,  # Changed from False
    }
)
```

### Customize Messages

Edit `models/helpdesk_ticket.py` and modify the notification messages:

```python
# Success message
ticket._show_notification(
    _('✓ Sync Complete'),  # Custom title
    _('Your ticket has been synced!'),  # Custom message
    'success'
)

# Warning message
ticket._show_notification(
    _('⚠ Partial Success'),
    _('Ticket synced with warnings. Check logs.'),
    'warning'
)

# Error message
ticket._show_notification(
    _('✗ Sync Error'),
    _('Could not sync. Try again later.'),
    'danger'
)
```

### Add Sound Notifications

To add sound to notifications, you can extend the notification:

```python
self.env['bus.bus']._sendone(
    self.env.user.partner_id,
    'simple_notification',
    {
        'title': title,
        'message': message,
        'type': odoo_type,
        'sticky': False,
        'className': 'o_notification_with_sound',  # Add sound
    }
)
```

---

## Visual Examples

### Success Notification
```
╔═══════════════════════════════════════════╗
║ ✅ API Sync Success                       ║
║ ─────────────────────────────────────────║
║ Ticket HELP-125 successfully synced      ║
║ with RAM Prime Care API                  ║
╚═══════════════════════════════════════════╝
```

### Warning Notification
```
╔═══════════════════════════════════════════╗
║ ⚠️ API Sync Warning                       ║
║ ─────────────────────────────────────────║
║ Ticket HELP-125 synced but API           ║
║ returned status 404                      ║
╚═══════════════════════════════════════════╝
```

### Error Notification
```
╔═══════════════════════════════════════════╗
║ 🚫 API Sync Failed                        ║
║ ─────────────────────────────────────────║
║ Failed to sync ticket HELP-125:          ║
║ Connection timeout                       ║
╚═══════════════════════════════════════════╝
```

---

## Testing Notifications

### Test Success Notification

1. Ensure RAM Prime Care API is accessible
2. Open a ticket
3. Change stage
4. You should see green success notification

### Test Warning Notification

To simulate a warning, temporarily change the API endpoint to return 404:

```python
# In models/helpdesk_ticket.py (temporary for testing)
base_url = 'https://ramprimecare.com/HISAdmin/api/nonexistent'
```

### Test Error Notification

To simulate an error, temporarily use an invalid URL:

```python
# In models/helpdesk_ticket.py (temporary for testing)
base_url = 'https://invalid-domain-that-does-not-exist.com/api'
```

Or reduce timeout to force timeout errors:

```python
response = requests.get(api_url, timeout=0.001)  # Very short timeout
```

---

## Benefits

✅ **Instant Feedback** - Users know immediately if sync succeeded  
✅ **Error Awareness** - Users are notified of issues right away  
✅ **Non-Intrusive** - Notifications auto-dismiss  
✅ **Professional UX** - Modern toast notification system  
✅ **Multilingual** - Uses Odoo's translation system `_()`  
✅ **No Blocking** - Notifications don't prevent ticket updates  

---

## Troubleshooting

### Notifications Not Appearing

**Issue:** Toast notifications don't show up

**Solutions:**

1. **Check Browser Console** - Look for JavaScript errors
2. **Clear Browser Cache** - Hard refresh (Ctrl+Shift+R)
3. **Check Bus Module** - Ensure `bus` module is installed
4. **Check User Session** - Log out and log back in
5. **Test with Other Users** - Verify it's not user-specific

### Notifications Appearing Multiple Times

**Issue:** Same notification shows twice

**Cause:** The `write()` method might be called multiple times

**Solution:** Already handled with `tickets_with_stage_change` tracking

---

## Future Enhancements

Potential improvements:

1. **Notification History** - Store notifications in database
2. **Sound Alerts** - Add audio feedback for errors
3. **Desktop Notifications** - Use browser push notifications
4. **Slack/Email** - Send notifications to external systems
5. **Retry Button** - Add action button to retry failed syncs

---

## Support

For issues with notifications:
- Check Odoo logs for errors
- Verify `bus.bus` model is accessible
- Test with minimal browser extensions
- Contact your Odoo development team


