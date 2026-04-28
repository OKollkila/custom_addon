# Installation Guide - TOP RAM API Integration

## Prerequisites

- Odoo 18 installed and running
- Helpdesk module installed
- Python 3.10 or higher
- Network access to ramprimecare.com

## Step-by-Step Installation

### 1. Install Python Dependencies

```bash
pip install requests>=2.31.0
```

Or if using a virtual environment:

```bash
source /path/to/odoo/venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. Deploy the Module

Copy the entire `top_ram_api` folder to your Odoo addons directory:

```bash
# Example for Docker setup
cp -r top_ram_api /path/to/odoo-18-docker/addons/

# Example for standard installation
cp -r top_ram_api /opt/odoo/addons/
```

### 3. Update Odoo Configuration (if needed)

Ensure your `odoo.conf` includes the addons path:

```ini
[options]
addons_path = /path/to/addons,/path/to/odoo-18-docker/addons
```

### 4. Restart Odoo Server

```bash
# For Docker
docker-compose restart

# For systemd service
sudo systemctl restart odoo

# For manual installation
./odoo-bin -c /etc/odoo/odoo.conf
```

### 5. Update Apps List

1. Log in to Odoo as Administrator
2. Go to **Apps** menu
3. Click on **Update Apps List**
4. Confirm the update

### 6. Install the Module

1. In the Apps menu, remove the "Apps" filter
2. Search for **"TOP RAM API"** or **"RAM Prime Care"**
3. Click **Install** on the "TOP RAM API Integration" module
4. Wait for installation to complete

### 7. Verify Installation

1. Go to **Helpdesk** → **Tickets**
2. Open any ticket (or create a new one)
3. Verify the **Workflow Level** field appears in the form view
4. Try changing the stage and check Odoo logs for API call confirmation

## Configuration

### Basic Configuration

No additional configuration needed - the module works out of the box!

### Advanced Configuration

#### Change API Endpoint

Edit `models/helpdesk_ticket.py`, line ~75:

```python
base_url = 'https://your-custom-endpoint.com/api/path'
```

#### Adjust API Timeout

Edit `models/helpdesk_ticket.py`, line ~85:

```python
response = requests.get(api_url, timeout=30)  # Change from 10 to 30 seconds
```

#### Change Date Format

Edit `models/helpdesk_ticket.py`, line ~69:

```python
update_time = fields.Datetime.now().strftime('%Y%m%d%H%M%S')  # YYYYMMDDHHmmSS format
```

#### Use POST Instead of GET

Edit `models/helpdesk_ticket.py`, line ~85:

```python
# Change from:
response = requests.get(api_url, timeout=10)

# To:
data = {
    'ticketId': ticket_id,
    'workFlowLevel': workflow_level,
    'status': status,
    'updateTime': update_time
}
response = requests.post(base_url, json=data, timeout=10)
```

## Troubleshooting

### Module Not Appearing in Apps List

**Problem**: Can't find the module after updating apps list

**Solutions**:
1. Check the module is in the correct addons path
2. Verify `__manifest__.py` exists and is valid Python
3. Check Odoo logs for module loading errors
4. Restart Odoo server with `--log-level=debug`

### Workflow Level Field Not Showing

**Problem**: Field doesn't appear in ticket form

**Solutions**:
1. Clear browser cache
2. Update the module: Apps → TOP RAM API Integration → Upgrade
3. Check if you have helpdesk module installed
4. Verify view inheritance is correct

### API Calls Failing

**Problem**: API not being called when stage changes

**Solutions**:

1. **Check Logs**: Go to Settings → Technical → Logging
   ```
   Look for: "Calling RAM API: https://ramprimecare.com/..."
   ```

2. **Test Network Connectivity**:
   ```bash
   curl https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/TEST/1/New/2025-10-09_12:00:00
   ```

3. **Verify requests Library**:
   ```bash
   python3 -c "import requests; print(requests.__version__)"
   ```

4. **Check Firewall**: Ensure outbound HTTPS traffic is allowed

5. **Enable Debug Logging**:
   Edit `models/helpdesk_ticket.py` and set logging to DEBUG:
   ```python
   _logger.setLevel(logging.DEBUG)
   ```

### Permission Errors

**Problem**: Users can't see/edit workflow level

**Solutions**:
1. The field inherits helpdesk.ticket permissions
2. Ensure users have proper Helpdesk access rights
3. No additional security rules needed

## Testing

### Manual Test

1. Create a new ticket: **Helpdesk → Tickets → Create**
2. Fill in basic information
3. Set **Workflow Level** to "Level 3"
4. Change **Stage** to "In Progress"
5. Check Odoo logs for:
   ```
   INFO ... Calling RAM API: https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask/TICKET-XXX/3/In Progress/2025-10-09_14:30:45
   INFO ... RAM API call successful for ticket TICKET-XXX
   ```

### Verify in External System

1. Check RAM Prime Care system for the updated ticket
2. Verify all parameters are received correctly

## Uninstallation

1. Go to **Apps** menu
2. Search for "TOP RAM API"
3. Click **Uninstall**
4. The `workflow_level` field data will be preserved in the database

## Upgrading

When a new version is available:

1. Replace the module folder with the new version
2. Restart Odoo
3. Go to Apps → TOP RAM API Integration
4. Click **Upgrade**

## Support Checklist

Before requesting support, please check:

- [ ] Odoo 18 is running
- [ ] Helpdesk module is installed
- [ ] `requests` library is installed
- [ ] Module appears in Apps list
- [ ] Module is installed (not just present)
- [ ] Odoo server has been restarted after installation
- [ ] Browser cache has been cleared
- [ ] Checked Odoo logs for errors
- [ ] Network connectivity to ramprimecare.com is working

## Logs Location

### Docker Installation
```bash
docker-compose logs -f odoo
```

### Standard Installation
```bash
tail -f /var/log/odoo/odoo-server.log
```

### Check Specific API Calls
```bash
grep "RAM API" /var/log/odoo/odoo-server.log
```

---

**Need Help?** Contact your Odoo development team with:
- Odoo version
- Module version
- Error logs
- Steps to reproduce the issue

