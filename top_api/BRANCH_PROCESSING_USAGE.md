# Branch Processing Usage Guide

## Overview
This module provides dynamic branch processing functionality that automatically loops through all branches in the `clinizone.branch` table and processes missed invoice data for each branch using their `prime_care_code` field.

## Key Features
- **Dynamic Branch Processing**: Automatically discovers and processes all branches with `prime_care_code`
- **Yesterday's Date**: Uses yesterday's date by default for data processing
- **Comprehensive Logging**: Detailed logging for each branch and overall process
- **Error Handling**: Robust error handling with branch-specific error tracking
- **API Endpoints**: REST API endpoints for manual testing and integration

## Scheduled Actions

### 1. Daily Branch Processing (3:30 AM)
```xml
<record id="ir_cron_process_all_branches" model="ir.cron">
    <field name="name">Process All Branches - Missed Invoices</field>
    <field name="code">model.cron_fetch_missed_invoices()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
</record>
```

### 2. Test Processing (Hourly - Disabled by default)
```xml
<record id="ir_cron_test_branch_processing" model="ir.cron">
    <field name="name">Test Branch Processing - Hourly</field>
    <field name="code">model.visit_branch()</field>
    <field name="active">False</field>
    <field name="interval_number">1</field>
    <field name="interval_type">hours</field>
</record>
```

## Python Methods

### 1. Process All Branches (Cron Method)
```python
# Automatically processes all branches with prime_care_code
result = self.env['crm.lead'].cron_fetch_missed_invoices()
```

### 2. Visit Specific Branch
```python
# Process specific branch by prime_care_code
result = self.env['crm.lead'].visit_branch('BRANCH001', '2024-01-15')

# Process all branches
result = self.env['crm.lead'].visit_branch()
```

### 3. Process Branch by ID
```python
# Process branch by database ID
result = self.env['crm.lead'].process_branch_by_id(5, '2024-01-15')
```

### 4. Get Branch Information
```python
# Get all branches with prime_care_code
info = self.env['crm.lead'].get_all_branches_info()
```

## API Endpoints

### 1. Process Branches
```
POST /api/branches/process
Content-Type: application/json
Authorization: Bearer <token>

{
    "branch_code": "BRANCH001",    // Optional: specific branch
    "branch_id": 5,                // Optional: branch by ID
    "date": "2024-01-15",          // Optional: target date
    "all_branches": true           // Optional: process all
}
```

### 2. Get Branch Information
```
GET /api/branches/info
Authorization: Bearer <token>
```

## Response Format

### Successful Processing
```json
{
    "success": true,
    "message": "Branch processing completed",
    "result": {
        "total_records": 150,
        "leads_created": 120,
        "leads_skipped": 25,
        "leads_failed": 5,
        "errors": [],
        "branch_results": {
            "Doha Medical Complex": {
                "code": "DMC001",
                "result": {
                    "total_records": 50,
                    "leads_created": 45,
                    "leads_skipped": 3,
                    "leads_failed": 2
                }
            }
        }
    }
}
```

### Branch Information
```json
{
    "total_branches": 3,
    "branches": [
        {
            "id": 1,
            "name": "Doha Medical Complex",
            "prime_care_code": "DMC001",
            "company_id": 1,
            "company_name": "Clinizone Medical",
            "city_id": 1,
            "city_name": "Doha"
        }
    ]
}
```

## Configuration

### System Parameters
- `missed_invoice.api_token`: API authentication token
- `missed_invoice.api_base_url`: API base URL
- `missed_invoice.default_company_id`: Default company ID for leads
- `missed_invoice.api_timeout`: API request timeout

### Branch Requirements
- Each branch must have a `prime_care_code` field populated
- The `prime_care_code` should match the branch code used by the external API

## Error Handling
- Individual branch failures don't stop the entire process
- Detailed error logging for each branch
- Comprehensive error reporting in response
- Automatic retry logic for API failures

## Performance Optimization
- Bulk lead creation for better performance
- Efficient database queries with proper indexing
- Comprehensive logging without performance impact
- Error isolation per branch
