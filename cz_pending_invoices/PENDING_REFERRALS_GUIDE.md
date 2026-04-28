# Pending Referrals Module Guide

## Overview
This module polls pending and rejected referrals from an external API with dynamic date parameters and stores them in Odoo for lead generation and tracking.

## API Endpoint
```
http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals?fromDate=YYYY-MM-DD
```

## Features
- ✅ **Scheduled API Polling** with dynamic dates
- ✅ **Comprehensive Data Storage** - 30+ fields from API
- ✅ **Lead Generation** - Create CRM leads from referrals
- ✅ **Rich Views** - List, form with tabs for reason/rejection
- ✅ **Smart Filtering** - By status, date, doctor, department
- ✅ **Duplicate Prevention** - Won't re-poll same date

## Installation

### 1. Upgrade the Module
```bash
odoo-bin -u cz_pending_invoices -d your_database
```

### 2. Configure API Settings
**Settings → Companies → Your Company → Pending Referrals Tab**
- **Pending Referral URL**: `http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals`
- **Pending Referral Token**: (optional if API requires authentication)

### 3. Activate Scheduled Action
**Settings → Technical → Automation → Scheduled Actions**
- Find: "Pull Pending Referrals"
- Set **Active** = True
- Default: Runs daily and fetches yesterday's referrals

## Usage

### Automatic (Recommended)
The cron job runs daily and automatically fetches yesterday's referrals.

### Manual Polling

#### From Odoo Shell:
```bash
odoo-bin shell -d your_database
```

```python
# Poll yesterday's referrals
env['cz.pending_referral_poll'].poll_yesterday()

# Poll today's referrals
env['cz.pending_referral_poll'].poll_today()

# Poll specific date
env['cz.pending_referral_poll'].poll_custom_date('2025-07-01')

# View referrals
referrals = env['cz.pending_referral'].search([])
print(f"Total referrals: {len(referrals)}")

# View pending referrals only
pending = env['cz.pending_referral'].search([('status', '=', 'Pending')])
for ref in pending:
    print(f"{ref.patient_name} - {ref.from_doctor} → {ref.to_doctor}")
```

#### From Python Code:
```python
# In any Odoo method
self.env['cz.pending_referral_poll'].poll_yesterday()
```

## Data Model

### cz.pending_referral
Stores referral records from the API.

**Patient Fields:**
- `patient_name` - Patient Name
- `mrno` - Medical Record Number
- `patient_id` - Patient ID

**Doctor Fields:**
- `from_doctor` - Referring Doctor
- `to_doctor` - Receiving Doctor
- `from_consultant_id` - From Consultant ID
- `to_consultant_id` - To Consultant ID
- `consultant_id` - Consultant ID

**Status Fields:**
- `status` - Pending/Rejected/etc.
- `visit_status` - Visit Status (in-progress, finished, etc.)
- `rejection_reason` - Why it was rejected

**Location Fields:**
- `branch` - Branch Code
- `department` - Department Code
- `speciality` - Medical Speciality
- `branch_id` - Computed Many2one to clinizone.branch
- `department_id` - Computed Many2one to clinizone.department

**Service & Details:**
- `service_name` - Service Name
- `reason` - Referral Reason
- `priority` - Priority Level
- `action` - Action to take

**Dates:**
- `requested_date` - When referral was requested
- `visit_date` - When visit is scheduled
- `date` - Poll date (when record was fetched)

**Financial:**
- `amount` - Amount
- `net_amt` - Net Amount
- `invoice_id` - Related Invoice

**Other:**
- `visit_no` - Visit Number
- `encounter_id` - Encounter ID
- `lead_id` - Related CRM Lead
- `description` - Computed HTML description

## API Response Mapping

The module automatically maps the API response fields:

```python
# API Response → Odoo Field
{
    "fromDoctor" → from_doctor,
    "toDoctor" → to_doctor,
    "visitStatus" → visit_status,
    "patientName" → patient_name,
    "mrno" → mrno,
    "serviceName" → service_name,
    "requestedDate" → requested_date (timestamp converted),
    "visitDate" → visit_date (timestamp converted),
    "status" → status,
    "reason" → reason,
    "rejectionReason" → rejection_reason,
    "branch" → branch,
    "department" → department,
    "speciality" → speciality,
    // ... and 15+ more fields
}
```

### Date Conversion
The API returns timestamps in milliseconds. These are automatically converted:

```python
# requestedDate: 1758182165353 → 2025-08-18 12:42:45
requested_date = datetime.fromtimestamp(int(timestamp) / 1000)
```

## Viewing Referrals

### Menu Location
**CRM → Pending Referrals**

### Available Filters
- **Pending** - Only pending referrals
- **Rejected** - Only rejected referrals
- **Today** - Fetched today
- **This Week** - Fetched this week
- **No Lead** - Referrals without CRM leads

### Group By Options
- Date
- Status
- Branch
- Department
- From Doctor
- To Doctor

## Lead Generation

### Automatic Button
Each referral has a "Create Lead" button in the form view.

### What It Creates
```python
{
    'company_id': From branch company,
    'treating_doctor': from_doctor,
    'patient_id': mrno,
    'name': patient_name,
    'contact_name': patient_name,
    'topic': 'Pending Referral - {status}',
    'campaign': 'Pending Referrals',
    'branch_id': Computed branch,
    'department_id': Computed department,
    'description': Full HTML description,
}
```

### Requirements for Lead Creation
- ✅ Branch must be identified (matched by prime_care_code)
- ✅ Department must be identified (matched by prime_care_code)
- ✅ No existing lead for this referral

## Form View Features

### Header
- **Create Lead Button** - Creates CRM lead (hidden if lead exists)
- **Status Bar** - Shows current status

### Tabs
1. **Reason** - Referral reason details
2. **Rejection Reason** - Why it was rejected (shown only if rejected)
3. **Full Description** - Complete HTML formatted information

### Sections
- Patient Information
- Status & Date
- Doctors (from/to consultants)
- Location (branch/department/speciality)
- Dates (requested/visit)
- Service & Financial
- Other Details

## API Response Example

Based on the actual API at `http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals?fromDate=2025-07-01`:

```json
[{
  "fromDoctor": "HEBTALLA AHMED",
  "toDoctor": "DALIA MOHAMED",
  "visitStatus": "in-progress",
  "patientName": "SREEN MUHAMMOD OUDAH",
  "mrno": "KHB10000029309",
  "requestedDate": 1758182165353,
  "reason": "27# ",
  "status": "Pending",
  "branch": null,
  "department": null,
  "encounterId": 0,
  "netAmt": 0.0,
  "rejectionReason": null
}]
```

## Scheduled Action Configuration

**File**: `demo/pending_referral_ir.cron.xml`

```xml
<field name="interval_type">days</field>
<field name="interval_number">1</field>
<field name="active">0</field>  <!-- Must enable manually -->
<field name="code">model.poll_yesterday()</field>
```

**Common Configurations:**
- Every hour: `interval_type="hours"`, `interval_number="1"`
- Every 6 hours: `interval_type="hours"`, `interval_number="6"`
- Every day: `interval_type="days"`, `interval_number="1"`
- Twice daily: `interval_type="hours"`, `interval_number="12"`

## Testing

### Test API Manually
```bash
curl "http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals?fromDate=2025-07-01"
```

### Test from Odoo Shell
```python
# Poll for specific date
env['cz.pending_referral_poll'].poll_custom_date('2025-07-01')

# Check results
referrals = env['cz.pending_referral'].search([('date', '=', '2025-07-01')])
print(f"Found {len(referrals)} referrals for 2025-07-01")

# View details
if referrals:
    ref = referrals[0]
    print(f"Patient: {ref.patient_name}")
    print(f"From: {ref.from_doctor}")
    print(f"To: {ref.to_doctor}")
    print(f"Status: {ref.status}")
    print(f"Reason: {ref.reason}")
```

### Check Logs
```bash
grep -i "referral\|poll" odoo.log | tail -30
```

Look for:
```
INFO: Starting referral poll for date: 2025-07-01
INFO: Calling Referral API: http://...
INFO: Received 23 referral(s)
INFO: Created referral record ID: 123 for patient John Doe
INFO: Referral poll completed successfully. Created 23 records.
```

## Troubleshooting

### No Data Appearing?
1. **Check API is accessible**:
   ```bash
   curl "http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals?fromDate=2025-07-01"
   ```

2. **Check company settings**:
   - Settings → Companies → Your Company → Pending Referrals
   - Verify URL is correct

3. **Check scheduled action**:
   - Settings → Technical → Scheduled Actions
   - "Pull Pending Referrals" should be Active

4. **Check logs**:
   ```bash
   grep "referral\|poll" odoo.log | tail -50
   ```

### API Errors?
- Verify API endpoint is accessible from Odoo server
- Check if authentication token is required
- Ensure date format is correct (YYYY-MM-DD)
- Check firewall/network access

### Field Errors?
All fields are already mapped based on the actual API response from:
`http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals?fromDate=2025-07-01`

The mapping should work out-of-the-box!

### Branch/Department Not Found?
The module looks up branches and departments by `prime_care_code`. Ensure:
- `clinizone.branch` records have correct `prime_care_code`
- `clinizone.department` records have correct `prime_care_code`
- API returns valid branch/department codes

### Lead Creation Fails?
Check logs for specific errors:
```python
_logger.error(f"Error for referral {referral.id}: {e}")
```

Common issues:
- Branch not identified
- Department not identified  
- Missing required fields in CRM lead model

## Security

Default access: **System Administrators only**

To grant access to other users, edit `security/ir.model.access.csv`:

```csv
access_pending_referral_user,access_pending_referral_user,model_cz_pending_referral,sales_team.group_sale_manager,1,1,1,0
```

## Files Created

```
models/
  ├── pending_referral.py              # Referral data model (30+ fields)
  └── pending_referral_poll.py         # API polling logic

views/
  ├── pending_referral_company.xml     # Company settings
  └── pending_referral/
      ├── action.xml                   # Window action
      ├── list.xml                     # List/form/search views
      └── menu.xml                     # Menu item

demo/
  └── pending_referral_ir.cron.xml     # Scheduled action

security/
  └── ir.model.access.csv              # Updated with access rights
```

## Integration with CRM

This module integrates seamlessly with your CRM module:
- Creates leads with all referral information
- Links back to original referral
- Populates branch, department, doctor information
- Rich HTML description for context

## Next Steps

1. ✅ Module installed
2. ⏳ Configure company settings
3. ⏳ Enable scheduled action
4. ⏳ Test manual polling
5. ⏳ Verify referrals appear in list
6. ⏳ Test lead creation
7. ⏳ Set up branch/department mappings

## Support

For issues or questions:
- Check the logs
- Verify API is accessible
- Review field mappings in `pending_referral_poll.py`
- Contact Surge Technologies development team

---

**Author**: Surge Technologies  
**License**: Other proprietary  
**Date**: October 2025

