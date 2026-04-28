# Bearer Token Configuration Guide

## Overview

The RAM Prime Care API requires a **Bearer Token** for authentication. This module now supports dynamic Bearer token configuration through Odoo's system parameters.

---

## ✅ Features

- **Dynamic Configuration**: Change Bearer token without modifying code
- **System Parameters**: Stored securely in Odoo database
- **Easy UI**: Configure through Helpdesk Settings page
- **Auto-Loaded**: Token is automatically included in API requests
- **Default Token**: Pre-configured with your token on installation

---

## 🚀 Quick Setup

### Method 1: Through Helpdesk Settings (Recommended) ⭐

1. **Go to Helpdesk Settings**
   - Navigate to: **Helpdesk → Configuration → Settings**

2. **Scroll to "RAM Prime Care API Integration" section**

3. **Enter your configuration**:
   - **Bearer Token**: Paste your JWT token
   - **API Endpoint**: Verify or update the API URL

4. **Click "Save"**

Done! ✅

---

### Method 2: Through System Parameters (Advanced)

1. **Enable Developer Mode**
   - Settings → Activate Developer Mode

2. **Go to System Parameters**
   - Settings → Technical → Parameters → System Parameters

3. **Find or create the parameter**:
   - **Key**: `top_ram_api.bearer_token`
   - **Value**: Your JWT Bearer token

4. **Optionally configure endpoint**:
   - **Key**: `top_ram_api.endpoint`
   - **Value**: `https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask`

5. **Save**

---

## 📋 Default Configuration

The module comes pre-configured with your test token:

```
Key: top_ram_api.bearer_token
Value: eyJraWQiOiJqd3QudGVjaG5hcy5rZXkiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

This is set during installation via `data/system_parameters.xml`.

---

## 🔧 How It Works

### API Request Headers

The module automatically adds these headers to every API call:

```http
Authorization: Bearer eyJraWQiOiJqd3QudGVjaG5hcy5rZXkiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json
Accept: application/json
```

### Code Implementation

In `models/helpdesk_ticket.py`:

```python
# Get Bearer token from system parameters
IrConfigParam = self.env['ir.config_parameter'].sudo()
bearer_token = IrConfigParam.get_param('top_ram_api.bearer_token', default='')

# Prepare headers with Bearer token
headers = {
    'Authorization': f'Bearer {bearer_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

# Make request with headers
response = requests.get(api_url, headers=headers, timeout=10)
```

---

## 🔐 Security Considerations

### Token Storage

- ✅ Stored in Odoo database (encrypted at rest if DB encryption is enabled)
- ✅ Only accessible to administrators
- ✅ Hidden in UI (password field)
- ✅ Not logged in plain text

### Best Practices

1. **Restrict Access**: Only give System Admin access to settings
2. **Rotate Tokens**: Update token periodically
3. **Monitor Logs**: Check for unauthorized access attempts
4. **Use HTTPS**: Always use secure connections

---

## 📝 Token Details

### Your Current Token

```
eyJraWQiOiJqd3QudGVjaG5hcy5rZXkiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMTE0Nzc5MzUgI2NsaW5pem9uZSIsInVwbiI6IjExMTQ3NzkzNSAjY2xpbml6b25lIiwiYXV0aF90aW1lIjoxNzQwMDUxMzMxLCJpc3MiOiJ0ZWNobmFzIiwiZ3JvdXBzIjpbXSwiZXhwIjoxNzQwMDY5MzMxMjA2LCJpYXQiOjE3NDAwNTEzMzF9.SDXYax1pqKcYqxWqN1yxY6MCBAQo2dqqI44Uc3S-R-pKnUEKkGdZkGT7-u1eUKPn_SEcIClasc_8bHqwDvCw390NGKTZaOcatFXey6NenfRHfNLk8wCkToCfTy1PxqlgutwBDwcA8dpJxsaECqH-DZagqo97N0ZwgrA27CQhizCQe-wvy9lSdx9ZVmSYVsOdsvRUXy-PTCkRPhhVatBpyELB2wRlID-78HO8YwcHsyXOtiXg727DvvqnMjRqktpSP-Dper1nOFqIbAqoDrcQ-nPcrzF6YBAT8g8AazZocOL7TPIDp4k2WKPYZ0XORjUBbm4Fsb8AcVX98mXgfqGaEQ
```

### Decoded Token Claims

```json
{
  "sub": "111477935 #clinizone",
  "upn": "111477935 #clinizone",
  "auth_time": 1740051331,
  "iss": "technas",
  "groups": [],
  "exp": 1740069331206,
  "iat": 1740051331
}
```

**Note**: This token expires on **2025-10-20 (exp: 1740069331)**. You'll need to update it before then!

---

## 🔄 Updating the Token

### When to Update

- Token is expired (check `exp` claim)
- Token is compromised
- Security policy requires rotation
- New token issued by API provider

### How to Update

#### Option 1: Via UI (Recommended)

1. Helpdesk → Configuration → Settings
2. Find "RAM Prime Care API Integration"
3. Clear old token and paste new token
4. Save

#### Option 2: Via System Parameters

1. Settings → Technical → System Parameters
2. Find `top_ram_api.bearer_token`
3. Edit value with new token
4. Save

#### Option 3: Via Code (For automation)

```python
self.env['ir.config_parameter'].sudo().set_param(
    'top_ram_api.bearer_token',
    'NEW_TOKEN_HERE'
)
```

---

## 🧪 Testing the Configuration

### Test API Call

After configuring the token, test it:

1. **Open a helpdesk ticket**
2. **Change the stage** (e.g., New → In Progress)
3. **Check the logs**:
   ```bash
   docker-compose logs -f odoo | grep "RAM API"
   ```

### Expected Log Output

**Success:**
```
INFO ... Calling RAM API: https://ramprimecare.com/... (with Bearer token)
INFO ... RAM API call successful for ticket HELP-001. Response: ...
```

**Token Error:**
```
WARNING ... RAM API call returned status 401 for ticket HELP-001. Response: Unauthorized
```

---

## 🐛 Troubleshooting

### Issue: 401 Unauthorized

**Cause**: Token is invalid, expired, or missing

**Solution**:
1. Check token is correctly copied (no spaces/line breaks)
2. Verify token hasn't expired
3. Request new token from API provider
4. Update system parameter

### Issue: Token Not Being Sent

**Cause**: System parameter not configured

**Solution**:
```bash
# Check if parameter exists
docker-compose exec odoo odoo shell -d your_database
>>> env['ir.config_parameter'].sudo().get_param('top_ram_api.bearer_token')
```

### Issue: 403 Forbidden

**Cause**: Token is valid but doesn't have required permissions

**Solution**:
- Contact API provider to grant necessary permissions
- Verify token scope/claims

---

## 📊 Monitoring

### Check Token Usage

View all API calls with token:

```bash
docker-compose logs -f odoo | grep "Calling RAM API.*with Bearer token"
```

### Check Authentication Errors

```bash
docker-compose logs -f odoo | grep "RAM API call returned status 401"
```

---

## 🔑 Token Management Best Practices

| Practice | Why |
|----------|-----|
| **Regular Rotation** | Reduce exposure window |
| **Secure Storage** | Protect from unauthorized access |
| **Audit Logging** | Track token usage |
| **Expiry Monitoring** | Prevent service disruption |
| **Least Privilege** | Only grant necessary permissions |

---

## 📚 Files Modified

| File | Purpose |
|------|---------|
| `models/helpdesk_ticket.py` | Added Bearer token retrieval and header configuration |
| `models/res_config_settings.py` | Added settings fields for token and endpoint |
| `data/system_parameters.xml` | Pre-configured default token on installation |
| `views/res_config_settings_views.xml` | Added UI for token configuration in settings |

---

## 🎯 Summary

✅ **Bearer token authentication is now active**  
✅ **Token is configurable through UI**  
✅ **Default token is pre-configured**  
✅ **Token is automatically added to all API requests**  
✅ **Endpoint is also configurable**  

---

## 📞 Support

For token-related issues:
1. Check logs for authentication errors
2. Verify token hasn't expired
3. Test with provided token first
4. Contact API provider for new tokens
5. Contact Odoo administrator for configuration help

---

**Last Updated**: 2025-10-09  
**Module Version**: 18.0.1.1.0

