# Multi Attendance Location API Documentation

## Overview

This feature allows employees to have multiple attendance locations based on Partner Assignments when the `allow_multi_attendance_location` checkbox is enabled.

## Implementation Details

### 1. Employee Model Extension

**Field Added:**
```python
allow_multi_attendance_location = fields.Boolean(
    string='Allow Multi Attendance Location',
    default=False,
    help='If enabled, employee can have multiple attendance locations from Partner Assignments'
)
```

**Location:** `models/hr_employee.py`

### 2. Employee Form View

**Checkbox Added:** After the `address_id` field in the Work Information tab

**Location:** `views/hr_employee_views.xml`

### 3. API Enhancement

**Modified Route:** `GET /api/hr/employees`

**New Behavior:** 
- When `allow_multi_attendance_location` is `True`: Returns all Partner Assignment children under the `address_id`
- When `allow_multi_attendance_location` is `False`: Returns only the `address_id` partner itself (default assignment)

## API Response Structure

### Work Schedule Information
The API now includes the employee's working hours for the current day:

- **`work_schedule`**: Object containing work schedule information
  - **`work_from`**: Start time in HH:MM format (e.g., "09:00")
  - **`work_to`**: End time in HH:MM format (e.g., "17:00") 
  - **`date`**: Current date in ISO format (e.g., "2024-01-15")
  - **`has_schedule`**: Boolean indicating if the employee has work scheduled for today

**Note**: If the employee has no work calendar assigned or no work scheduled for today, `work_from` and `work_to` will be `null` and `has_schedule` will be `false`.

### Standard Response (when checkbox is False - Default Assignment Only)
```json
{
  "ok": true,
  "count": 1,
  "records": [
    {
      "id": 123,
      "name": "John Doe",
      "work_email": "john@company.com",
      "address_id": 456,
      "allow_multi_attendance_location": false,
      "work_schedule": {
        "work_from": "09:00",
        "work_to": "17:00",
        "date": "2024-01-15",
        "has_schedule": true
      },
      "partner_assignments": [
        {
          "id": 456,
          "name": "Main Office",
          "email": "main@company.com",
          "phone": "+1-555-0100",
          "geolocation": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy_distance": 5.0,
            "has_geolocation": true
          },
          "address": {
            "street": "123 Main Street",
            "city": "New York",
            "state": "NY",
            "country": "United States"
          },
          "active": true,
          "is_default_assignment": true
        }
      ],
      "partner_assignments_count": 1,
      "partner_latitude": 40.7128,
      "partner_longitude": -74.0060,
      "image_url": "/web/image/hr.employee/123/image_1920"
    }
  ]
}
```

### Enhanced Response (when checkbox is True - All Child Assignments)
```json
{
  "ok": true,
  "count": 1,
  "records": [
    {
      "id": 123,
      "name": "John Doe",
      "work_email": "john@company.com",
      "address_id": 456,
      "allow_multi_attendance_location": true,
      "work_schedule": {
        "work_from": "09:00",
        "work_to": "17:00",
        "date": "2024-01-15",
        "has_schedule": true
      },
      "partner_assignments": [
        {
          "id": 789,
          "name": "Office Location A",
          "email": "office-a@company.com",
          "phone": "+1-555-0101",
          "mobile": "+1-555-0102",
          "title": "Mr.",
          "function": "Office Manager",
          "geolocation": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy_distance": 5.0,
            "has_geolocation": true
          },
          "address": {
            "street": "123 Main Street",
            "street2": "Suite 100",
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "country": "United States"
          },
          "active": true,
          "is_default_assignment": false
        },
        {
          "id": 790,
          "name": "Office Location B",
          "email": "office-b@company.com",
          "phone": "+1-555-0201",
          "mobile": "+1-555-0202",
          "title": "Ms.",
          "function": "Branch Manager",
          "geolocation": {
            "latitude": 40.7589,
            "longitude": -73.9851,
            "accuracy_distance": 3.0,
            "has_geolocation": true
          },
          "address": {
            "street": "456 Broadway",
            "street2": "Floor 5",
            "city": "New York",
            "state": "NY",
            "zip": "10013",
            "country": "United States"
          },
          "active": true,
          "is_default_assignment": false
        }
      ],
      "partner_assignments_count": 2,
      "partner_latitude": 40.7128,
      "partner_longitude": -74.0060,
      "image_url": "/web/image/hr.employee/123/image_1920"
    }
  ]
}
```

## Usage Examples

### 1. Get Employee with Multi Location Enabled
```bash
curl -X GET "http://localhost:10018/api/hr/employees?id=123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Get All Employees (will include Partner Assignments for those with checkbox enabled)
```bash
curl -X GET "http://localhost:10018/api/hr/employees" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Get Employee by PIN
```bash
curl -X GET "http://localhost:10018/api/hr/employees?pin=1234" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Key Features

### 1. Smart Assignment Loading
- **When `allow_multi_attendance_location` is `True`**: Returns all child Partner Assignments under the `address_id`
- **When `allow_multi_attendance_location` is `False`**: Returns only the `address_id` partner itself (default assignment)
- Always provides at least one assignment location for attendance purposes
- Improves performance by loading only relevant data

### 2. Complete Partner Assignment Data
Each Partner Assignment includes:
- **Basic Info**: ID, name, email, phone, mobile, title, function
- **Geolocation**: Latitude, longitude, accuracy distance, availability flag
- **Address**: Complete address information
- **Status**: Active/inactive status
- **Assignment Type**: `is_default_assignment` flag to identify default vs. child assignments

### 3. Error Handling
- Graceful error handling if Partner Assignment data cannot be retrieved
- Logs warnings for debugging purposes
- Returns empty arrays instead of failing the entire request

### 4. Backward Compatibility
- Existing API consumers continue to work without changes
- New fields are added without breaking existing functionality
- Default values ensure consistent response structure
- Always returns at least one assignment (default or children)


## Database Structure

### Employee Table
```sql
-- New field added to hr_employee table
ALTER TABLE hr_employee ADD COLUMN allow_multi_attendance_location BOOLEAN DEFAULT FALSE;
```

### Partner Assignment Relationship
```
hr_employee.address_id (parent partner)
    ├── Default Assignment: address_id partner itself
    └── Child Assignments: res.partner (child contacts/assignments)
        ├── partner_latitude
        ├── partner_longitude
        └── geolocation_accuracy_distance
```

## Configuration Steps

1. **Install the module** - Adds the checkbox field and API enhancement
2. **Enable checkbox** - Set `allow_multi_attendance_location = True` for employees who need multiple locations
3. **Create Partner Assignments** - Add child contacts under the employee's address_id partner
4. **Set geolocation data** - Add latitude, longitude, and accuracy distance to Partner Assignments
5. **Use API** - Call the enhanced `/api/hr/employees` endpoint

## Benefits

- ✅ **Flexible Attendance**: Employees can check in/out from multiple locations
- ✅ **Geolocation Accuracy**: Each location has its own accuracy distance
- ✅ **Performance Optimized**: Only loads data when needed
- ✅ **Backward Compatible**: Existing systems continue to work
- ✅ **Complete Data**: Full Partner Assignment information in API response
- ✅ **Error Resilient**: Graceful handling of data retrieval issues
