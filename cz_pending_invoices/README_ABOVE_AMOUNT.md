# Above Amount Invoice Module

## Overview
This module extends the Missed Invoices module to poll invoices above a certain amount from an external API with dynamic date parameters.

## Features
- **Scheduled API Polling**: Automatically calls the API with dynamic dates
- **Data Storage**: Stores invoice data in Odoo database
- **List/Form Views**: View and manage invoices through Odoo interface
- **Company Configuration**: Easy API URL and authentication setup
- **Multiple Date Options**: Poll yesterday, today, or custom dates

## API Endpoint
```
http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=YYYY-MM-DD
```

## Installation

1. **Upgrade the module** after adding these files:
   ```bash
   odoo-bin -u cz_pending_invoices -d your_database
   ```

2. **Configure the API settings**:
   - Go to **Settings → Companies → Your Company**
   - Open the **Above Amount Invoices** tab
   - Set the **Above Amount Invoice URL**: `http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount`
   - (Optional) Set the **Above Amount Invoice Token** if authentication is required

3. **Activate the Scheduled Action**:
   - Go to **Settings → Technical → Automation → Scheduled Actions**
   - Find "Pull Invoices Above Amount"
   - Set **Active** to True
   - The cron will run daily and fetch invoices from yesterday

## Usage

### Automatic Polling (Recommended)
The scheduled action runs daily and automatically fetches invoices from yesterday.

### Manual Polling

#### From Python Code:
```python
# Poll yesterday's invoices
self.env['cz.above_amount_invoice_poll'].poll_yesterday()

# Poll today's invoices
self.env['cz.above_amount_invoice_poll'].poll_today()

# Poll specific date
from datetime import datetime
target_date = datetime(2025, 8, 18).date()
self.env['cz.above_amount_invoice_poll'].poll_custom_date(target_date)
```

#### From Odoo Shell:
```python
# Poll yesterday
env['cz.above_amount_invoice_poll'].poll_yesterday()

# Poll specific date
env['cz.above_amount_invoice_poll'].poll_custom_date('2025-08-18')
```

## Data Models

### cz.above_amount_invoice
Stores the invoice records fetched from the API.

**Key Fields:**
- `invoice_id`: Invoice ID
- `invoice_number`: Invoice Number
- `invoice_date`: Invoice Date
- `patient_name`: Patient Name
- `patient_id`: Patient ID
- `amount`: Invoice Amount
- `branch`: Branch Code
- `department`: Department Code
- `consultant_name`: Consultant Name
- `payment_status`: Payment Status
- `date`: Poll Date (when the record was fetched)

### cz.above_amount_invoice_poll
Tracks polling history to prevent duplicate fetches.

**States:**
- `new`: Polling not started
- `done`: Successfully completed
- `error`: Failed with error

## API Response Mapping

**Important**: Adjust the field mapping in `above_amount_invoice_poll.py` based on your actual API response structure.

Current mapping (example):
```python
invoice_vals = {
    'invoice_id': invoice_data.get('invoiceId'),
    'invoice_number': invoice_data.get('invoiceNumber'),
    'patient_name': invoice_data.get('patientName'),
    # ... add more fields as needed
}
```

## Customization

### Adjust Fields Based on API Response

1. **Examine your API response** first:
   ```bash
   curl "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=2025-08-18"
   ```

2. **Update the model** in `models/above_amount_invoice.py`:
   - Add/remove fields to match API response
   - Update the `_compute_description` method

3. **Update the polling logic** in `models/above_amount_invoice_poll.py`:
   - Modify the `invoice_vals` dictionary in the `do_poll` method
   - Map API response fields to model fields

4. **Update the views** in `views/above_amount_invoice/list.xml`:
   - Add/remove columns in the list view
   - Update form view layout

### Schedule Configuration

Modify the cron job in `demo/above_amount_ir.cron.xml`:
```xml
<field name="interval_type">days</field>  <!-- or hours, weeks, months -->
<field name="interval_number">1</field>   <!-- run every 1 day -->
```

## Viewing Invoices

1. Go to **CRM → Invoices Above Amount** menu
2. Use filters to view:
   - Today's invoices
   - This week's invoices
   - Group by date, branch, or department

## Troubleshooting

### Check Logs
Look for these log messages:
```
INFO: Starting poll for date: YYYY-MM-DD
INFO: Calling API: http://...
INFO: Received X invoice(s)
INFO: Poll completed successfully
```

### Common Issues

1. **No data appearing**:
   - Check API URL in company settings
   - Verify scheduled action is active
   - Check Odoo logs for errors
   - Test API manually with curl/Postman

2. **API errors**:
   - Verify API endpoint is accessible
   - Check if authentication token is required
   - Ensure date format is correct (YYYY-MM-DD)

3. **Field mapping errors**:
   - Compare API response structure with model fields
   - Update field mappings in `do_poll` method
   - Check Odoo logs for field-related errors

## Security

By default, only system administrators can access these records. To grant access to other users:

1. Edit `security/ir.model.access.csv`
2. Add lines for your custom groups
3. Upgrade the module

## Development Notes

- The module follows Odoo 18 best practices
- Uses proper field dependencies with `@api.depends`
- Implements error handling and logging
- Prevents duplicate polling with unique date constraint
- Supports both bearer token authentication and open APIs

## Files Added

```
models/
  ├── above_amount_invoice.py          # Invoice data model
  └── above_amount_invoice_poll.py     # Polling logic model

views/
  ├── above_amount_company.xml         # Company settings view
  └── above_amount_invoice/
      ├── action.xml                   # Window action
      ├── list.xml                     # List & form views
      └── menu.xml                     # Menu item

demo/
  └── above_amount_ir.cron.xml        # Scheduled action

security/
  └── ir.model.access.csv              # Updated with new models
```

## Support

For issues or questions, contact the development team at Surge Technologies.

