# ⚙️ Configuration Guide

## Bearer Token Configuration

The module is pre-configured with your Bearer token. To change it:

### Method: System Parameters

1. **Enable Developer Mode**
   - Settings → Activate Developer Mode (bottom of page)

2. **Go to System Parameters**
   - Settings → Technical → Parameters → System Parameters

3. **Configure Bearer Token**
   - Click "Create" or find existing parameter
   - **Key**: `top_ram_api.bearer_token`
   - **Value**: Your JWT Bearer token
   - Click "Save"

4. **Configure API Endpoint (Optional)**
   - Click "Create" or find existing parameter
   - **Key**: `top_ram_api.endpoint`
   - **Value**: `https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask`
   - Click "Save"

---

## Pre-Configured Values

The module installs with these default values:

| Parameter | Value |
|-----------|-------|
| `top_ram_api.bearer_token` | Your JWT token (pre-configured) |
| `top_ram_api.endpoint` | `https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask` |

---

## Quick Test

After installation:

1. **Open a helpdesk ticket**
2. **Set Workflow Level** (1-10)
3. **Change Stage** (e.g., New → In Progress)
4. **Check ticket chatter** for sync message
5. **Check logs**: `docker-compose logs -f odoo | grep "RAM API"`

---

## Troubleshooting

### Check if token is configured:
```bash
# In Odoo shell
docker-compose exec odoo odoo shell -d your_database
>>> env['ir.config_parameter'].sudo().get_param('top_ram_api.bearer_token')
```

### Update token via shell:
```python
env['ir.config_parameter'].sudo().set_param(
    'top_ram_api.bearer_token',
    'YOUR_NEW_TOKEN_HERE'
)
```

---

## Security Note

The Bearer token is stored in the database and only accessible to administrators with access to System Parameters.

