# Changelog

All notable changes to the TOP RAM API Integration module.

## [18.0.1.1.0] - 2025-10-09

### ✨ Added - Toast Notifications

#### New Feature: Real-Time Visual Feedback

Users now receive **instant toast notifications** when ticket stages change and API calls are made.

**What's New:**

- ✅ **Success Notifications** (Green) - When API returns HTTP 200
- ⚠️ **Warning Notifications** (Orange) - When API returns non-200 status
- 🚫 **Error Notifications** (Red) - When API call fails (timeout, network error)

**Technical Changes:**

1. **New Method:** `_show_notification()` in `models/helpdesk_ticket.py`
   - Displays toast notifications using Odoo's bus system
   - Auto-dismissing notifications
   - Color-coded by status type

2. **Enhanced `write()` Method:**
   - Now captures API response status
   - Triggers appropriate notification based on response
   - Non-blocking error handling with user feedback

3. **Documentation:**
   - New file: `TOAST_NOTIFICATIONS.md` - Complete notification guide
   - Updated: `README.md` - Added notification section
   - Updated: `QUICKSTART.md` - Added visual examples
   - Updated: `static/description/index.html` - Added feature highlight

**User Experience:**

Before:
```
User changes stage → API called → (silent) → Check logs to verify
```

After:
```
User changes stage → API called → Toast appears → User gets instant feedback
```

**Code Example:**

```python
# Success notification
ticket._show_notification(
    _('API Sync Success'),
    _('Ticket %s successfully synced with RAM Prime Care API') % ticket.name,
    'success'
)
```

---

## [18.0.1.0.0] - 2025-10-09

### 🎉 Initial Release

#### Features

- **Workflow Level Field:** Added selection field (1-10) to helpdesk tickets
- **API Integration:** Automatic API calls on stage changes
- **External Sync:** Integrates with RAM Prime Care API
- **Error Handling:** Robust exception handling and logging
- **Non-Blocking:** Ticket updates proceed even if API fails

#### Models

- Extended `helpdesk.ticket` model with `workflow_level` field
- Override `write()` method to detect stage changes
- API call method `_call_ram_api()` with timeout protection

#### Views

- Form view: Added workflow_level field after stage_id
- List view: Added workflow_level column (optional)
- Search view: Added filters for levels 1-5 and group by

#### API Integration

**Endpoint:**
```
https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/
{ticketId}/{workFlowLevel}/{status}/{updateTime}
```

**Parameters:**
- `ticketId`: Ticket name
- `workFlowLevel`: Selected level (1-10)
- `status`: New stage name
- `updateTime`: Timestamp (YYYY-MM-DD_HH:MM:SS)

#### Documentation

- `README.md` - Complete feature documentation
- `INSTALLATION.md` - Step-by-step installation guide
- `QUICKSTART.md` - 5-minute quick start
- `requirements.txt` - Python dependencies
- `static/description/index.html` - App store description

#### Dependencies

- Odoo 18
- helpdesk module
- Python requests library (>=2.31.0)

---

## Version Numbering

Format: `[Odoo Version].[Major].[Minor].[Patch]`

- **18** = Odoo version
- **0** = Module major version
- **1** = Module minor version (feature additions)
- **0/1** = Patch version (bug fixes)

Examples:
- `18.0.1.0.0` = Initial release for Odoo 18
- `18.0.1.1.0` = Added toast notifications
- `18.0.1.1.1` = Bug fix for notifications

---

## Upgrade Instructions

### From 18.0.1.0.0 to 18.0.1.1.0

No database upgrade needed. Just update the module:

1. Replace module files
2. Restart Odoo
3. Apps → TOP RAM API Integration → Upgrade
4. Clear browser cache

Toast notifications will work immediately after upgrade.

---

## Roadmap

### Planned Features

- [ ] Manual retry button for failed syncs
- [ ] Notification history/log viewer
- [ ] Configurable notification preferences per user
- [ ] Email notifications for critical errors
- [ ] Batch sync for multiple tickets
- [ ] API endpoint configuration from UI
- [ ] Webhook support (push notifications from API)

### Under Consideration

- [ ] Desktop push notifications
- [ ] Slack/Teams integration
- [ ] API call queue with retry logic
- [ ] Performance metrics dashboard
- [ ] Multi-language API support

---

## Bug Fixes

### 18.0.1.1.0
- None (feature release)

### 18.0.1.0.0
- Initial release

---

## Breaking Changes

### 18.0.1.1.0
- None (backward compatible)

### 18.0.1.0.0
- Initial release

---

## Security

No security vulnerabilities reported.

**Security Considerations:**
- API calls use HTTPS
- No sensitive data logged
- Timeout protection prevents hanging
- Non-blocking to prevent DoS

---

## Contributors

- Development Team
- Odoo Community

---

## Support

For issues, bug reports, or feature requests:
- Check documentation first
- Review logs for errors
- Contact your Odoo development team

---

## License

LGPL-3

