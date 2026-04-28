# API Response Mapping Guide

## ⚠️ IMPORTANT: Customize This Based on Your Actual API

This guide shows how to map your API response fields to the Odoo model fields.

## Step 1: Test Your API

First, call your API to see the actual response structure:

```bash
curl "http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount?fromDate=2025-08-18"
```

## Step 2: Understand the Response Structure

Your API might return something like this (example):

```json
[
  {
    "invoiceId": "INV-12345",
    "invoiceNumber": "INV-2025-001",
    "invoiceDate": "2025-08-18T10:30:00",
    "patientName": "John Doe",
    "patientId": "P12345",
    "totalAmount": 5000.00,
    "branchCode": "BR001",
    "departmentCode": "CARDIO",
    "doctorName": "Dr. Smith",
    "status": "Pending"
  }
]
```

## Step 3: Update the Model (if needed)

**File**: `models/above_amount_invoice.py`

If your API has different fields, add them to the model:

```python
class AboveAmountInvoice(models.Model):
    _name = 'cz.above_amount_invoice'
    
    # Add any fields that match your API response
    invoice_id = fields.Char('Invoice ID')
    invoice_number = fields.Char('Invoice Number')
    invoice_date = fields.Datetime('Invoice Date')
    patient_name = fields.Char('Patient Name')
    
    # Add more fields as needed from your API
    additional_field = fields.Char('Additional Field')
```

## Step 4: Update the Field Mapping

**File**: `models/above_amount_invoice_poll.py` (around line 90)

### Current Example Mapping:

```python
invoice_vals = {
    'date': date,
    'invoice_id': invoice_data.get('invoiceId'),
    'invoice_number': invoice_data.get('invoiceNumber'),
    'invoice_date': invoice_data.get('invoiceDate'),
    'patient_name': invoice_data.get('patientName'),
    'patient_id': invoice_data.get('patientId'),
    'amount': invoice_data.get('amount'),
    'branch': invoice_data.get('branch', '').strip(),
    'department': invoice_data.get('department', '').strip(),
    'consultant_name': invoice_data.get('consultantName'),
    'payment_status': invoice_data.get('paymentStatus'),
}
```

### How to Customize:

1. **Match API field names** (case-sensitive):
   - If API returns `InvoiceID` (capital ID), use: `invoice_data.get('InvoiceID')`
   - If API returns `invoice_id` (lowercase), use: `invoice_data.get('invoice_id')`

2. **Handle nested objects**:
   ```python
   # If API returns: {"patient": {"name": "John", "id": "P123"}}
   'patient_name': invoice_data.get('patient', {}).get('name'),
   'patient_id': invoice_data.get('patient', {}).get('id'),
   ```

3. **Convert data types**:
   ```python
   # String to float
   'amount': float(invoice_data.get('amount', 0)),
   
   # String to datetime
   from datetime import datetime
   'invoice_date': datetime.strptime(invoice_data.get('date'), '%Y-%m-%d'),
   
   # Timestamp to datetime
   'invoice_date': datetime.fromtimestamp(int(invoice_data.get('timestamp')) / 1000),
   ```

4. **Provide defaults**:
   ```python
   'branch': invoice_data.get('branch', 'UNKNOWN').strip(),
   'amount': invoice_data.get('amount', 0.0),
   ```

## Real-World Example Scenarios

### Scenario 1: API uses different field names

**API Response:**
```json
{
  "inv_id": "12345",
  "inv_no": "INV-001",
  "pat_name": "John Doe"
}
```

**Mapping:**
```python
invoice_vals = {
    'invoice_id': invoice_data.get('inv_id'),
    'invoice_number': invoice_data.get('inv_no'),
    'patient_name': invoice_data.get('pat_name'),
}
```

### Scenario 2: Nested data structure

**API Response:**
```json
{
  "invoice": {
    "id": "12345",
    "details": {
      "number": "INV-001",
      "date": "2025-08-18"
    }
  },
  "patient": {
    "name": "John Doe",
    "mrn": "P12345"
  }
}
```

**Mapping:**
```python
invoice_vals = {
    'invoice_id': invoice_data.get('invoice', {}).get('id'),
    'invoice_number': invoice_data.get('invoice', {}).get('details', {}).get('number'),
    'invoice_date': invoice_data.get('invoice', {}).get('details', {}).get('date'),
    'patient_name': invoice_data.get('patient', {}).get('name'),
    'patient_id': invoice_data.get('patient', {}).get('mrn'),
}
```

### Scenario 3: Date/Time conversion needed

**API Response:**
```json
{
  "invoiceDate": "18/08/2025",
  "timestamp": 1692352800000
}
```

**Mapping:**
```python
from datetime import datetime

# Convert DD/MM/YYYY to datetime
date_str = invoice_data.get('invoiceDate')
invoice_date = datetime.strptime(date_str, '%d/%m/%Y') if date_str else False

# Convert timestamp (milliseconds) to datetime
timestamp = invoice_data.get('timestamp')
invoice_datetime = datetime.fromtimestamp(int(timestamp) / 1000) if timestamp else False

invoice_vals = {
    'invoice_date': invoice_date,
}
```

### Scenario 4: API returns single object instead of array

**API Response:**
```json
{
  "invoiceId": "12345",
  "patientName": "John Doe"
}
```

**Already handled!** The code already handles both:
```python
# This code is already in the file
for invoice_data in invoices_data if isinstance(invoices_data, list) else [invoices_data]:
    # Process each invoice
```

## Step 5: Update Views (optional)

If you added new fields, update the list view to display them:

**File**: `views/above_amount_invoice/list.xml`

```xml
<list string="Invoices Above Amount">
    <field name="date"/>
    <field name="invoice_number"/>
    <field name="patient_name"/>
    <field name="amount"/>
    <!-- Add your new fields here -->
    <field name="your_new_field"/>
</list>
```

## Step 6: Test

After making changes:

1. **Upgrade the module:**
   ```bash
   odoo-bin -u cz_pending_invoices -d your_database
   ```

2. **Test from Odoo shell:**
   ```bash
   odoo-bin shell -d your_database
   ```
   ```python
   # Test with a specific date
   env['cz.above_amount_invoice_poll'].poll_custom_date('2025-08-18')
   
   # Check if data was created
   invoices = env['cz.above_amount_invoice'].search([])
   print(f"Found {len(invoices)} invoices")
   
   # View first invoice data
   if invoices:
       inv = invoices[0]
       print(f"Invoice: {inv.invoice_number}")
       print(f"Patient: {inv.patient_name}")
       print(f"Amount: {inv.amount}")
   ```

3. **Check logs for errors:**
   ```bash
   grep -i "error\|exception" odoo.log | tail -20
   ```

## Common Field Type Mappings

| Odoo Field Type | API Data Type | Example |
|----------------|---------------|---------|
| `fields.Char()` | String | `"John Doe"` |
| `fields.Float()` | Number | `5000.50` |
| `fields.Integer()` | Integer | `123` |
| `fields.Boolean()` | Boolean | `true` / `false` |
| `fields.Date()` | String | `"2025-08-18"` |
| `fields.Datetime()` | String/Timestamp | `"2025-08-18T10:30:00"` |
| `fields.Text()` | Long string | `"Long description..."` |
| `fields.Json()` | Object/Array | `{"key": "value"}` |

## Data Type Conversion Examples

```python
# String to Float
'amount': float(invoice_data.get('amount', 0)),

# String to Integer
'count': int(invoice_data.get('count', 0)),

# String to Boolean
'is_paid': invoice_data.get('status') == 'Paid',

# String date to Date object
from datetime import datetime
'invoice_date': datetime.strptime(invoice_data.get('date'), '%Y-%m-%d').date(),

# String datetime to Datetime object
'created_at': datetime.strptime(invoice_data.get('created'), '%Y-%m-%d %H:%M:%S'),

# Timestamp (seconds) to Datetime
'created_at': datetime.fromtimestamp(int(invoice_data.get('timestamp'))),

# Timestamp (milliseconds) to Datetime
'created_at': datetime.fromtimestamp(int(invoice_data.get('timestamp')) / 1000),
```

## Debugging Tips

### Print the API response to see structure:

Add this to `do_poll` method after `response.json()`:

```python
invoices_data = response.json()
_logger.info(f"API Response: {invoices_data}")  # This will show structure in logs
```

### Print each field as you map it:

```python
for invoice_data in invoices_data if isinstance(invoices_data, list) else [invoices_data]:
    _logger.info(f"Processing invoice: {invoice_data}")
    
    invoice_vals = {
        'invoice_id': invoice_data.get('invoiceId'),
        # ... more fields
    }
    
    _logger.info(f"Mapped values: {invoice_vals}")
```

### Handle missing fields gracefully:

```python
# Don't fail if field is missing
'patient_name': invoice_data.get('patientName', 'Unknown'),
'amount': invoice_data.get('amount', 0.0),
'branch': invoice_data.get('branch', '').strip(),
```

## Need Help?

1. Print the API response to see actual structure
2. Check Odoo logs for errors
3. Review the full README_ABOVE_AMOUNT.md
4. Contact Surge Technologies development team

## Quick Reference

**Main file to edit:** `models/above_amount_invoice_poll.py` (line ~90)

**What to change:** The `invoice_vals` dictionary

**How to test:** `env['cz.above_amount_invoice_poll'].poll_custom_date('2025-08-18')`

**Check logs:** `grep "poll\|invoice" odoo.log`

