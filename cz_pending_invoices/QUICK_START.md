# Quick Start Guide - Above Amount Invoice Module

## Installation (3 Steps)

### 1. Upgrade the Module
```bash
odoo-bin -u cz_pending_invoices -d your_database
```

### 2. Configure API Settings
**Settings → Companies → Your Company → Above Amount Invoices Tab**
- **Above Amount Invoice URL**: `http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount`
- **Above Amount Invoice Token**: (optional, if API requires authentication)

### 3. Activate Scheduled Action
**Settings → Technical → Automation → Scheduled Actions**
- Find: "Pull Invoices Above Amount"
- Set **Active** to **True**
- Default: Runs daily

---

## Quick Commands

### From Odoo Shell
```bash
# Open shell
odoo-bin shell -d your_database
```

```python
# Poll yesterday's invoices
env['cz.above_amount_invoice_poll'].poll_yesterday()

# Poll today's invoices
env['cz.above_amount_invoice_poll'].poll_today()

# Poll specific date
env['cz.above_amount_invoice_poll'].poll_custom_date('2025-08-18')

# View invoices
invoices = env['cz.above_amount_invoice'].search([])
print(f"Total invoices: {len(invoices)}")

# View today's invoices
from datetime import datetime
today = datetime.today().strftime('%Y-%m-%d')
today_invoices = env['cz.above_amount_invoice'].search([('date', '=', today)])
for inv in today_invoices:
    print(f"{inv.patient_name} - {inv.amount}")
```

### From Python Code
```python
# In any Odoo method
self.env['cz.above_amount_invoice_poll'].poll_yesterday()
```

---

## View Invoices

**Menu**: CRM → Invoices Above Amount

**Filters**:
- Today
- This Week
- Group by Date/Branch/Department

---

## Test API Manually

```bash
# Test without authentication
curl "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=2025-08-18"

# Test with authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=2025-08-18"
```

---

## Customize Field Mapping

⚠️ **REQUIRED**: Update based on your actual API response

**File**: `models/above_amount_invoice_poll.py` (around line 90)

```python
# Current mapping (example)
invoice_vals = {
    'invoice_id': invoice_data.get('invoiceId'),
    'patient_name': invoice_data.get('patientName'),
    # Add your actual field names here
}
```

**Steps**:
1. Test API to see response structure
2. Update `invoice_vals` dictionary with correct field names
3. Add/remove fields in `models/above_amount_invoice.py` if needed
4. Upgrade module

---

## Troubleshooting

### No Data Appearing?
1. Check logs: `grep "poll" odoo.log`
2. Verify API is accessible
3. Check company settings
4. Ensure scheduled action is active

### API Errors?
1. Test API manually with curl
2. Check if authentication required
3. Verify date format (YYYY-MM-DD)

### Field Errors?
1. Compare API response with model fields
2. Update field mappings
3. Check field types match (Char, Float, Datetime, etc.)

---

## Scheduled Action Configuration

**File**: `demo/above_amount_ir.cron.xml`

```xml
<field name="interval_type">days</field>     <!-- Change to hours/weeks/months -->
<field name="interval_number">1</field>      <!-- Run every X intervals -->
<field name="active">0</field>               <!-- Set to 1 for auto-active -->
```

**Common Schedules**:
- Every hour: `interval_type="hours"`, `interval_number="1"`
- Every 6 hours: `interval_type="hours"`, `interval_number="6"`
- Every day at midnight: `interval_type="days"`, `interval_number="1"`

---

## File Structure

```
cz_pending_invoices/
├── models/
│   ├── above_amount_invoice.py          ← Invoice data model
│   ├── above_amount_invoice_poll.py     ← API polling logic ⚡
│   └── company.py                       ← API settings
├── views/
│   ├── above_amount_company.xml         ← Settings view
│   └── above_amount_invoice/
│       ├── action.xml
│       ├── list.xml                     ← List/Form views
│       └── menu.xml
├── demo/
│   └── above_amount_ir.cron.xml         ← Scheduled action
└── security/
    └── ir.model.access.csv              ← Access rights
```

⚡ = Main file to customize for your API

---

## Support Files

- **README_ABOVE_AMOUNT.md** - Full documentation
- **IMPLEMENTATION_SUMMARY.md** - Technical overview
- **QUICK_START.md** - This file

---

## Need Help?

1. Check the full **README_ABOVE_AMOUNT.md**
2. Review Odoo logs
3. Contact Surge Technologies development team

---

## License

Other proprietary - Surge Technologies

