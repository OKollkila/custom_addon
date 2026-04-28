# Quick Reference Card - API Polling Modules

## 🚀 Installation (3 Commands)

```bash
# 1. Upgrade module
odoo-bin -u cz_pending_invoices -d your_database

# 2. Configure (via shell)
odoo-bin shell -d your_database
```

```python
# 3. Set URLs in system parameters
env['ir.config_parameter'].sudo().set_param('cz_pending_invoices.above_amount_invoice_url', 'http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount')
env['ir.config_parameter'].sudo().set_param('cz_pending_invoices.pending_referral_url', 'http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals')
env.cr.commit()
```

---

## ⚙️ System Parameters (Recommended Way)

**Location**: Settings → Technical → Parameters → System Parameters

| Key | Value |
|-----|-------|
| `cz_pending_invoices.above_amount_invoice_url` | `http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount` |
| `cz_pending_invoices.above_amount_invoice_token` | (your token if needed) |
| `cz_pending_invoices.pending_referral_url` | `http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals` |
| `cz_pending_invoices.pending_referral_token` | (your token if needed) |

---

## 📋 Menu Locations

```
CRM
├── Missed Invoices (original)
├── Invoices Above Amount ← NEW
└── Pending Referrals ← NEW
```

---

## 🔄 Manual Polling Commands

```python
# Above Amount Invoice
env['cz.above_amount_invoice_poll'].poll_yesterday()
env['cz.above_amount_invoice_poll'].poll_today()
env['cz.above_amount_invoice_poll'].poll_custom_date('2025-08-18')

# Pending Referrals
env['cz.pending_referral_poll'].poll_yesterday()
env['cz.pending_referral_poll'].poll_today()
env['cz.pending_referral_poll'].poll_custom_date('2025-07-01')
```

---

## 📊 View Data

```python
# Count records
invoices = env['cz.above_amount_invoice'].search([])
referrals = env['cz.pending_referral'].search([])
print(f"Invoices: {len(invoices)}, Referrals: {len(referrals)}")

# View details
for inv in invoices[:5]:
    print(f"{inv.patient_name} - {inv.amount}")

for ref in referrals[:5]:
    print(f"{ref.patient_name} - {ref.from_doctor} → {ref.to_doctor}")
```

---

## ⏰ Enable Scheduled Actions

**Settings → Technical → Automation → Scheduled Actions**

1. Find "Pull Invoices Above Amount" → Set Active = True
2. Find "Pull Pending Referrals" → Set Active = True

Both run daily by default.

---

## 🧪 Test APIs Manually

```bash
# Test Above Amount Invoice
curl "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=2025-08-18"

# Test Pending Referrals
curl "http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals?fromDate=2025-07-01"
```

---

## 🔍 Check Configuration

```python
# View all system parameters
params = env['ir.config_parameter'].sudo().search([('key', 'like', 'cz_pending_invoices.%')])
for p in params:
    print(f"{p.key} = {p.value}")
```

---

## 📝 Check Logs

```bash
# View polling logs
grep -i "poll\|api" odoo.log | tail -30

# View specific module
grep "above_amount\|referral" odoo.log | tail -20
```

---

## 🎯 Lead Generation (Referrals Only)

```python
# Create leads for referrals without leads
referrals = env['cz.pending_referral'].search([('lead_id', '=', False)])
referrals.action_create_leads()
```

Or use the **"Create Lead"** button in the form view.

---

## 🔧 Common Tasks

### Change API URL
```python
env['ir.config_parameter'].sudo().set_param('cz_pending_invoices.above_amount_invoice_url', 'NEW_URL')
env.cr.commit()
```

### Add Authentication Token
```python
env['ir.config_parameter'].sudo().set_param('cz_pending_invoices.above_amount_invoice_token', 'YOUR_TOKEN')
env.cr.commit()
```

### Poll Specific Date Range
```python
from datetime import datetime, timedelta

# Poll last 7 days
for i in range(7):
    date = (datetime.today() - timedelta(days=i)).strftime('%Y-%m-%d')
    env['cz.above_amount_invoice_poll'].poll_custom_date(date)
    env['cz.pending_referral_poll'].poll_custom_date(date)
```

---

## 🐛 Troubleshooting

### No data appearing?
1. Check system parameters are set
2. Test API with curl
3. Check logs: `grep "poll" odoo.log`
4. Verify scheduled actions are active

### API errors?
1. Verify URL is accessible
2. Check if token is required
3. Ensure date format is YYYY-MM-DD

### Field errors?
All fields already mapped from real API responses!

---

## 📚 Documentation Files

- **QUICK_START.md** ← Start here
- **SYSTEM_PARAMETERS_GUIDE.md** ← URL configuration
- **README_ABOVE_AMOUNT.md** ← Invoice module
- **PENDING_REFERRALS_GUIDE.md** ← Referral module
- **COMPLETE_IMPLEMENTATION_SUMMARY.md** ← Overview

---

## 🎯 Models Created

| Model | Description |
|-------|-------------|
| `cz.above_amount_invoice` | Invoice records above amount |
| `cz.above_amount_invoice_poll` | Invoice polling logic |
| `cz.pending_referral` | Pending/rejected referrals |
| `cz.pending_referral_poll` | Referral polling logic |

---

## ⚡ Pro Tips

1. **Always test manually first** before enabling cron
2. **Use system parameters** for URLs (not company settings)
3. **Check logs** after first poll
4. **Test API with curl** to verify structure
5. **Enable one cron at a time**

---

## 📞 Support

1. Check documentation files
2. Review logs
3. Test API manually
4. Contact Surge Technologies team

---

**Quick Install Checklist**:
- [ ] Module upgraded
- [ ] System parameters configured
- [ ] Scheduled actions enabled
- [ ] Manual poll tested
- [ ] Data visible in menus
- [ ] Logs show success

---

**Created**: October 2025 | **Author**: Surge Technologies | **License**: Proprietary

