# System Parameters Configuration Guide

## Overview

The API URLs and authentication tokens are now configured using **System Parameters** instead of (or in addition to) company settings. This provides:

✅ **Centralized Configuration** - One place for all API settings  
✅ **Environment Flexibility** - Easy to change for dev/staging/production  
✅ **No Database Changes** - Update via UI without code changes  
✅ **Fallback Support** - Falls back to company settings if not set  

## System Parameters

### Location
**Settings → Technical → Parameters → System Parameters**

### Available Parameters

| Parameter Key | Description | Default Value |
|--------------|-------------|---------------|
| `cz_pending_invoices.above_amount_invoice_url` | Above Amount Invoice API URL | `http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount` |
| `cz_pending_invoices.above_amount_invoice_token` | Bearer token for Above Amount API | (empty) |
| `cz_pending_invoices.pending_referral_url` | Pending Referral API URL | `http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals` |
| `cz_pending_invoices.pending_referral_token` | Bearer token for Referral API | (empty) |

## How to Configure

### Method 1: Via Odoo UI (Recommended)

1. **Navigate to System Parameters**
   - Go to **Settings**
   - Click **Technical → Parameters → System Parameters**

2. **Find or Create Parameter**
   - Search for the parameter key (e.g., `cz_pending_invoices.above_amount_invoice_url`)
   - If it exists, click to edit
   - If not, click **Create**

3. **Set the Value**
   - **Key**: `cz_pending_invoices.above_amount_invoice_url`
   - **Value**: Your API URL
   - Click **Save**

4. **Repeat for Token (if needed)**
   - **Key**: `cz_pending_invoices.above_amount_invoice_token`
   - **Value**: Your bearer token
   - Click **Save**

### Method 2: Via Odoo Shell

```bash
odoo-bin shell -d your_database
```

```python
# Set Above Amount Invoice URL
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.above_amount_invoice_url',
    'http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount'
)

# Set Above Amount Invoice Token
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.above_amount_invoice_token',
    'your_bearer_token_here'
)

# Set Pending Referral URL
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.pending_referral_url',
    'http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals'
)

# Set Pending Referral Token
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.pending_referral_token',
    'your_bearer_token_here'
)

# Commit the changes
env.cr.commit()
```

### Method 3: Via SQL (Advanced)

```sql
-- Set Above Amount Invoice URL
INSERT INTO ir_config_parameter (key, value, create_date, write_date, create_uid, write_uid)
VALUES (
    'cz_pending_invoices.above_amount_invoice_url',
    'http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount',
    NOW(), NOW(), 1, 1
)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();

-- Set Pending Referral URL
INSERT INTO ir_config_parameter (key, value, create_date, write_date, create_uid, write_uid)
VALUES (
    'cz_pending_invoices.pending_referral_url',
    'http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals',
    NOW(), NOW(), 1, 1
)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();
```

## How It Works

### Priority Order

The system checks parameters in this order:

1. **System Parameter** (highest priority)
2. **Company Setting** (fallback)
3. **Error if neither found**

### Code Example

```python
# From above_amount_invoice_poll.py
IrConfigParameter = self.env['ir.config_parameter'].sudo()
url = IrConfigParameter.get_param('cz_pending_invoices.above_amount_invoice_url')

# Fallback to company setting if system parameter not set
if not url:
    url = self.env.company.above_amount_invoice_url

if not url:
    _logger.error('No API URL configured')
    return False
```

## Environment-Specific Configuration

### Development Environment

```python
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.above_amount_invoice_url',
    'http://dev-server:8080/HISAdmin/api/invoice/invoicesAboveAnAmount'
)
```

### Staging Environment

```python
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.above_amount_invoice_url',
    'http://staging-server:8080/HISAdmin/api/invoice/invoicesAboveAnAmount'
)
```

### Production Environment

```python
env['ir.config_parameter'].sudo().set_param(
    'cz_pending_invoices.above_amount_invoice_url',
    'http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount'
)
```

## Viewing Current Configuration

### Via Odoo Shell

```python
# Get all API-related parameters
params = env['ir.config_parameter'].sudo().search([
    ('key', 'like', 'cz_pending_invoices.%')
])

for param in params:
    print(f"{param.key} = {param.value}")
```

### Expected Output

```
cz_pending_invoices.above_amount_invoice_url = http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount
cz_pending_invoices.above_amount_invoice_token = 
cz_pending_invoices.pending_referral_url = http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals
cz_pending_invoices.pending_referral_token = 
```

## Testing Configuration

### Test Above Amount Invoice

```python
# Test reading the parameter
url = env['ir.config_parameter'].sudo().get_param('cz_pending_invoices.above_amount_invoice_url')
print(f"Above Amount URL: {url}")

# Test the API call
env['cz.above_amount_invoice_poll'].poll_custom_date('2025-08-18')
```

### Test Pending Referral

```python
# Test reading the parameter
url = env['ir.config_parameter'].sudo().get_param('cz_pending_invoices.pending_referral_url')
print(f"Pending Referral URL: {url}")

# Test the API call
env['cz.pending_referral_poll'].poll_custom_date('2025-07-01')
```

## Migration from Company Settings

If you were using company settings before, you can migrate:

```python
# Read from company
company = env.company

# Migrate to system parameters
if company.above_amount_invoice_url:
    env['ir.config_parameter'].sudo().set_param(
        'cz_pending_invoices.above_amount_invoice_url',
        company.above_amount_invoice_url
    )

if company.above_amount_invoice_token:
    env['ir.config_parameter'].sudo().set_param(
        'cz_pending_invoices.above_amount_invoice_token',
        company.above_amount_invoice_token
    )

if company.pending_referral_url:
    env['ir.config_parameter'].sudo().set_param(
        'cz_pending_invoices.pending_referral_url',
        company.pending_referral_url
    )

if company.pending_referral_token:
    env['ir.config_parameter'].sudo().set_param(
        'cz_pending_invoices.pending_referral_token',
        company.pending_referral_token
    )

env.cr.commit()
print("Migration completed!")
```

## Export/Import Configuration

### Export Configuration

```python
# Export to dictionary
config = {}
params = env['ir.config_parameter'].sudo().search([
    ('key', 'like', 'cz_pending_invoices.%')
])

for param in params:
    config[param.key] = param.value

import json
print(json.dumps(config, indent=2))
```

### Import Configuration

```python
import json

config = {
    "cz_pending_invoices.above_amount_invoice_url": "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount",
    "cz_pending_invoices.above_amount_invoice_token": "",
    "cz_pending_invoices.pending_referral_url": "http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals",
    "cz_pending_invoices.pending_referral_token": ""
}

for key, value in config.items():
    env['ir.config_parameter'].sudo().set_param(key, value)

env.cr.commit()
```

## Security Considerations

### Token Storage
- Tokens are stored in plaintext in the database
- Only accessible to system administrators
- Consider using environment variables for sensitive tokens in production

### Access Control
- System parameters require **Settings** access
- Only administrators can modify
- Use `sudo()` in code to access parameters

## Troubleshooting

### Parameter Not Found

```python
# Check if parameter exists
param = env['ir.config_parameter'].sudo().search([
    ('key', '=', 'cz_pending_invoices.above_amount_invoice_url')
])

if not param:
    print("Parameter not found! Creating...")
    env['ir.config_parameter'].sudo().set_param(
        'cz_pending_invoices.above_amount_invoice_url',
        'http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount'
    )
else:
    print(f"Parameter found: {param.value}")
```

### API Not Working

1. **Check parameter value**:
   ```python
   url = env['ir.config_parameter'].sudo().get_param('cz_pending_invoices.above_amount_invoice_url')
   print(f"Configured URL: {url}")
   ```

2. **Check logs**:
   ```bash
   grep "API URL configured" odoo.log
   ```

3. **Test manually**:
   ```bash
   curl "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=2025-08-18"
   ```

## Advantages Over Company Settings

| Feature | System Parameters | Company Settings |
|---------|------------------|------------------|
| **Centralized** | ✅ One place for all settings | ❌ Per company |
| **Easy to Change** | ✅ Via UI without code | ⚠️ Requires company access |
| **Multi-Company** | ✅ Shared across companies | ❌ Per company only |
| **Version Control** | ✅ Can export/import | ⚠️ In database only |
| **Environment Specific** | ✅ Easy to change | ⚠️ Requires migration |

## Best Practices

1. **Use System Parameters for URLs** - More flexible
2. **Keep Company Settings as Fallback** - Backward compatibility
3. **Document Configuration** - Keep track of what's set where
4. **Use Environment Variables in Production** - For sensitive tokens
5. **Test After Changes** - Always verify API calls work

## Quick Reference

### Set URL (Shell)
```python
env['ir.config_parameter'].sudo().set_param('cz_pending_invoices.above_amount_invoice_url', 'YOUR_URL')
env.cr.commit()
```

### Get URL (Code)
```python
url = self.env['ir.config_parameter'].sudo().get_param('cz_pending_invoices.above_amount_invoice_url')
```

### View All (Shell)
```python
params = env['ir.config_parameter'].sudo().search([('key', 'like', 'cz_pending_invoices.%')])
for p in params: print(f"{p.key} = {p.value}")
```

---

**Updated**: October 2025  
**Author**: Surge Technologies

