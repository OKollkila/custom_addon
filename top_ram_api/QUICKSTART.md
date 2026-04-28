# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Installation

```bash
# 1. Install Python dependency
pip install requests

# 2. Module is already in your addons folder!
# Location: d:\HUB\odoo-18-docker\addons\top_ram_api

# 3. Restart Odoo (Docker)
docker-compose restart

# 4. In Odoo: Apps → Update Apps List → Search "TOP RAM" → Install
```

### Usage

1. **Open a Helpdesk Ticket**
   - Go to Helpdesk → Tickets
   - Open existing or create new ticket

2. **Set Workflow Level**
   - Find the "Workflow Level" field (after Stage field)
   - Select a level from 1 to 10

3. **Change Stage**
   - Change the ticket stage (e.g., New → In Progress)
   - API is automatically called!
   - **🎉 Toast notification appears** showing sync status

### What You'll See

After changing the stage, a toast notification appears in the top-right corner:

**✅ Success (Green):**
```
API Sync Success
Ticket TICKET-001 successfully synced with RAM Prime Care API
```

**⚠️ Warning (Orange):**
```
API Sync Warning
Ticket TICKET-001 synced but API returned status 404
```

**🚫 Error (Red):**
```
API Sync Failed
Failed to sync ticket TICKET-001: Connection timeout
```

### Verify It's Working

Check Odoo logs:
```bash
docker-compose logs -f odoo | grep "RAM API"
```

You should see:
```
INFO ... Calling RAM API: https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/...
INFO ... RAM API call successful for ticket ...
```

### API Call Format

When you change a ticket stage, this URL is called:

```
https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/{ticketId}/{workFlowLevel}/{status}/{updateTime}
```

**Example:**
```
https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/TICKET-001/5/In%20Progress/2025-10-09_14:30:45
```

### Parameters Explained

| Parameter | Source | Example |
|-----------|--------|---------|
| `ticketId` | Ticket name | `TICKET-001` |
| `workFlowLevel` | Workflow Level field | `5` |
| `status` | New stage name | `In Progress` |
| `updateTime` | Current timestamp | `2025-10-09_14:30:45` |

### Common Issues

**Field not showing?**
- Clear browser cache (Ctrl+Shift+Del)
- Upgrade module: Apps → TOP RAM API → Upgrade

**API not being called?**
- Check logs for errors
- Verify network connectivity: `curl https://ramprimecare.com`
- Ensure `requests` library is installed

**Permission errors?**
- User needs Helpdesk access rights
- No additional permissions required

### Next Steps

- Read [README.md](README.md) for detailed features
- Check [INSTALLATION.md](INSTALLATION.md) for advanced configuration
- Customize API endpoint in `models/helpdesk_ticket.py` if needed

---

**That's it!** Your tickets now automatically sync with RAM Prime Care API. 🎉

