from odoo import http, fields, models, exceptions, _
from odoo.http import request
from datetime import datetime
from datetime import timedelta
from werkzeug.wrappers import Response
from markupsafe import Markup
import pytz
import logging
import json
import base64

_logger = logging.getLogger(__name__)

def error_response(exception, message):
    return {
        "error": {
            "type": type(exception).__name__,
            "message": message
        }
    }
def get_image_url(record, image_field='image_1920'):
    """
    Generates a URL for the image of a given record.
    This function can be used across all Odoo modules.

    Args:
        record (Record): The Odoo record for which the image URL should be generated.
        image_field (str): The field name of the image, default is 'image_1920'.

    Returns:
        str: The URL to access the image or None if the image doesn't exist.
    """
    if hasattr(record, image_field) and getattr(record, image_field):
        # Correcting the model name encoding issue by ensuring proper formatting
        model_name = record._name.replace('.', '%2E')
        image_route = f'/web/image/{model_name}/{record.id}/{image_field}'
        return request.httprequest.host_url.rstrip('/') + '/' + image_route
    else:
        return None

   
   
def format_datetime(dt, tz_name='Africa/Cairo'):
    """Format datetime to a string in ISO 8601 format and convert to local timezone."""
    if not dt or isinstance(dt, bool):  # Handle None or False values gracefully
        return None
    tz = pytz.timezone(tz_name)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%Y-%m-%dT%H:%M:%S")


def format_datetime(dt, tz_name='Africa/Cairo'):
    """Format datetime to a string in ISO 8601 format and convert to local timezone."""
    if not dt or isinstance(dt, bool):  # Handle None or False values gracefully
        return None
    tz = pytz.timezone(tz_name)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%Y-%m-%dT%H:%M:%S")

def convert_decimal_to_time(decimal_hours):
    """Convert a decimal representation of hours into HH:MM format."""
    if decimal_hours is None:
        return None
    hours = int(decimal_hours)
    minutes = int((decimal_hours - hours) * 60)
    return f"{hours:02}:{minutes:02}"
def post_map_link(record, latitude, longitude, address):
        link = f"https://maps.google.com/maps?q={latitude},{longitude}&z=18"
        map_link = f'<a href="{link}" target="_blank" rel="noreferrer noopener">{link}   </a>'
        record.message_post(
            body=Markup(map_link),  # Directly using the map link without wrapping in any additional tags
            subtype_xmlid="mail.mt_note",
            message_type='comment'  # Ensuring the message is treated as a comment
        )  
class EmployeeHRFunctions(http.Controller):
    
    # Attendance with geolocation and timestamp for check-in and check-out
    @http.route('/api/employee/attendance', type='json', auth="user", methods=['POST'], csrf=False)
    def register_attendance(self, **post):
        try:
            data = post.get('data', {})
            employee_id = data.get('employee_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            ip = data.get('ip')
            address_id = data.get('address_id')
            country = data.get('country')
            city = data.get('city')
            action = data.get('action')  # Either 'check_in' or 'check_out'
            timestamp = fields.Datetime.now()
            browser = data.get('browser', 'mobile app')
            if not employee_id:
                raise exceptions.ValidationError("employee_id is required")
            if not action or action not in ['check_in', 'check_out']:
                raise exceptions.ValidationError("action must be either 'check_in' or 'check_out'")

            employee = request.env['hr.employee'].browse(employee_id).ensure_one()

            if action == 'check_in':
                # Allow multiple check-ins per day - always create new attendance record
                attendance = request.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': timestamp,
                    'in_latitude': latitude,
                    'in_longitude': longitude,
                    'in_mode': 'manual',
                    'in_browser': browser,
                    'in_ip_address': ip,
                    'in_country_name': country,
                    'in_city': city,
                    'address_id': address_id
                })
                message = "Check-in recorded successfully"
                post_map_link(attendance, latitude, longitude, address_id)
                
            else:  # action == 'check_out'
                # Find the most recent check-in without check-out for this employee
                active_attendance = request.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], order='check_in desc', limit=1)
                
                if not active_attendance:
                    raise exceptions.ValidationError("No active check-in found for the employee. Please check in first.")
                
                # Update the active attendance with checkout information
                active_attendance.write({
                    'check_out': timestamp,
                    'out_latitude': latitude,
                    'out_longitude': longitude,
                    'out_mode': 'manual',
                    'out_browser': browser,
                    'out_ip_address': ip,
                    'out_country_name': country,
                    'out_city': city,
                    'out_address_id': address_id
                })
                message = "Check-out recorded successfully"
                post_map_link(active_attendance, latitude, longitude, address_id)
                attendance = active_attendance
                
            return {"attendance_id": attendance.id, "message": message}
        
        except Exception as e:
            _logger.error(f"Failed to register attendance: {str(e)}")
            return error_response(e, str(e))
    
    @http.route('/api/employee/<int:employee_id>/attendance/status', type='json', auth="user", methods=['GET'], csrf=False)
    def get_attendance_status(self, employee_id, **post):
        """
        Get the current attendance status for an employee.
        Returns whether the employee has an active check-in (no check-out).
        """
        try:
            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
            # Find the most recent check-in without check-out
            active_attendance = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], order='check_in desc', limit=1)
            
            if active_attendance:
                return {
                    "has_active_checkin": True,
                    "check_in_time": active_attendance.check_in.isoformat(),
                    "attendance_id": active_attendance.id,
                    "address": active_attendance.address_id.name if active_attendance.address_id else None
                }
            else:
                return {
                    "has_active_checkin": False,
                    "check_in_time": None,
                    "attendance_id": None,
                    "address": None
                }
                
        except Exception as e:
            _logger.error(f"Failed to get attendance status: {str(e)}")
            return error_response(e, str(e))
        
        
    
    @http.route('/api/employee/<int:employee_id>/attendances', type='http', auth="user", methods=['GET'], csrf=False)
    def get_attendance_records(self, employee_id, **params):
        try:
            attendances = request.env['hr.attendance'].search([('employee_id', '=', employee_id)])

            # Initialize an empty list to collect attendance data
            attendance_data = []


            # Iterate over each attendance record and prepare the response data
            for attendance in attendances:
                attendance_record = {
                    'attendance_id': attendance.id,
                    'employee_id': attendance.employee_id.id,
                    'employee_name': attendance.employee_id.name,
                    'check_in': format_datetime(attendance.check_in),
                    'check_out': format_datetime(attendance.check_out),
                    'worked_hours': convert_decimal_to_time(attendance.worked_hours),
                    'overtime_hours': convert_decimal_to_time(attendance.overtime_hours),
                    "in_latitude": attendance.in_latitude,
                    "in_longitude": attendance.in_longitude,
                    "in_country_name": attendance.in_country_name,
                    "in_city": attendance.in_city,
                    "in_browser": attendance.in_browser,
                    "out_latitude": attendance.out_latitude,
                    "out_longitude": attendance.out_longitude,
                    "out_country_name": attendance.out_country_name,
                    "out_city": attendance.out_city,
                    "out_browser": attendance.out_browser
                  
                }
                # Add the record to the list
                attendance_data.append(attendance_record)

            response_data = {"attendances": attendance_data}

            # Use request.make_response to create an HTTP response with the proper JSON formatting
            return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

        except Exception as e:
            _logger.error(f"Failed to fetch attendance records: {str(e)}")
            error_data = {
                'status': 'error',
                'message': str(e)
            }
            return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])






































    @http.route('/api/employee/<int:employee_id>/last_attendance_status', type='http', auth="user", methods=['GET'], csrf=False)
    def get_last_attendance_with_status(self, employee_id, **params):
        try: 
            # Retrieve the employee record
            employee = request.env['hr.employee'].browse(employee_id).ensure_one()

            if not employee:
                raise exceptions.ValidationError("Invalid employee ID")

            # Retrieve the last attendance record for the employee
            last_attendance = request.env['hr.attendance'].search([('employee_id', '=', employee.id)], order='check_in desc', limit=1)

            if not last_attendance:
                # No attendance records found for this employee
                response_data = {
                    'status': 'success',
                    'message': 'No attendance records found for this employee',
                    'last_attendance': None
                }
            else:
                # Determine the status based on whether check_out is present
                attendance_status = "check-in" if not last_attendance.check_out else "check-out"
                def convert_decimal_to_time(decimal_hours):
                    """Convert a decimal representation of hours into HH:MM format."""
                    if decimal_hours is None:
                        return None
                    # Split the hours and minutes
                    hours = int(decimal_hours)  # Get the integer part as hours
                    minutes = int((decimal_hours - hours) * 60)  # Get the fractional part and convert it to minutes
                    return f"{hours:02}:{minutes:02}"
            
                # Create response data for the last attendance
                last_attendance_data = {
                    'attendance_id': last_attendance.id,
                    'employee_id': last_attendance.employee_id.id,
                    'employee_name': last_attendance.employee_id.name,
                    'check_in': format_datetime(last_attendance.check_in) if last_attendance.check_in else None,
                    'check_out': format_datetime(last_attendance.check_out) if last_attendance.check_out else None,
                    'worked_hours': convert_decimal_to_time(last_attendance.worked_hours),
                    "overtime_hours":convert_decimal_to_time(last_attendance.overtime_hours) ,
                    "in_latitude": last_attendance.in_latitude,
                    "in_longitude": last_attendance.in_longitude,
                    "in_country_name": last_attendance.in_country_name,
                    "in_city": last_attendance.in_city,
                    "in_browser": last_attendance.in_browser,
                    "out_latitude": last_attendance.out_latitude,
                    "out_longitude": last_attendance.out_longitude,
                    "out_country_name": last_attendance.out_country_name,
                    "out_city": last_attendance.out_city,
                    "out_browser": last_attendance.out_browser,
                    "status": attendance_status  # Added status indicating check-in or check-out
                }

                response_data = {
                    'status': 'success',
                    'last_attendance': last_attendance_data
                }

            # Use request.make_response to return a proper JSON HTTP response
            return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

        except Exception as e:
            _logger.error(f"Failed to fetch last attendance with status: {str(e)}")
            error_data = {
                'status': 'error',
                'message': str(e)
            }
            return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])


#time_off_balance

    @http.route('/api/employee/<int:employee_id>/time_off_balance', type='http', auth="user", methods=['GET'], csrf=False)
    def get_time_off_balance(self, employee_id, **params):
        try:
            if not employee_id:
                raise exceptions.ValidationError("employee_id is required")

            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
            # Get allocation_status parameter from URL (default: 'all')
            allocation_status = params.get('allocation_status', 'all').lower()
            
            # Validate allocation_status parameter
            valid_statuses = ['all', 'with_allocation', 'without_allocation']
            if allocation_status not in valid_statuses:
                raise exceptions.ValidationError(f"Invalid allocation_status. Must be one of: {', '.join(valid_statuses)}")

            balances = []
            
            if allocation_status in ['all', 'with_allocation']:
                # Retrieve leave allocations for the employee
                allocations = request.env['hr.leave.allocation'].search([('employee_id', '=', employee.id), ('state', '=', 'validate')])

                for allocation in allocations:
                    # Retrieve leave requests of the employee for the same leave type to calculate used days
                    leave_requests = request.env['hr.leave'].search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', allocation.holiday_status_id.id),
                        ('state', 'in', ['confirm', 'validate'])
                    ])
                    
                    used_days = sum(leave.number_of_days for leave in leave_requests)
                    remaining_days = allocation.number_of_days - used_days

                    balances.append({
                        'time_off_id': allocation.holiday_status_id.id,
                        'time_off_type': allocation.holiday_status_id.name,
                        'allocated_days': allocation.number_of_days,
                        'remaining_days': remaining_days,
                        'used_days': used_days,
                        'has_allocation': True,
                        'support_document': getattr(allocation.holiday_status_id, 'support_document', False),
                    })
            
            if allocation_status in ['all', 'without_allocation']:
                # Get all leave types that have no allocation for the entire company
                # First, get all leave types in the system
                all_leave_types = request.env['hr.leave.type'].search([])
                
                # Get all allocated leave types for the entire company
                company_allocated_leave_types = request.env['hr.leave.allocation'].search([
                    ('employee_id.company_id', '=', employee.company_id.id),
                    ('state', '=', 'validate')
                ]).mapped('holiday_status_id')
                
                # Find leave types without any allocation in the company
                leave_types_without_allocation = all_leave_types - company_allocated_leave_types
                
                for leave_type in leave_types_without_allocation:
                    # Calculate used days for this leave type by the specific employee
                    leave_requests = request.env['hr.leave'].search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', leave_type.id),
                        ('state', 'in', ['confirm', 'validate'])
                    ])
                    
                    used_days = sum(leave.number_of_days for leave in leave_requests)

                    balances.append({
                        'time_off_id': leave_type.id,
                        'time_off_type': leave_type.name,
                        'allocated_days': 0,
                        'remaining_days': 0,
                        'used_days': used_days,
                        'has_allocation': False,
                        'support_document': getattr(leave_type, 'support_document', False),
                    })

            response_data = {
                'status': 'success',
                'time_off_balances': balances
            }

            # Use json_response to return a proper JSON HTTP response
            return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

        except Exception as e:
            error_data = {
                'status': 'error',
                'message': str(e),
            }
            return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])


        # Time off request
    @http.route('/api/employee/time_off', type='json', auth="user", methods=['POST'], csrf=False)
    def request_time_off(self, **post):
        try:
            data = post.get('data', {})
            employee_id = data.get('employee_id')
            reason = data.get('reason')
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            time_off_type_id = data.get('time_off_type_id')
            supported_attachment_ids = data.get('supported_attachment_ids', [])  # List of attachment data

            if not all([employee_id, date_from, date_to, time_off_type_id]):
                raise exceptions.ValidationError("employee_id, date_from, date_to, and time_off_type_id are required")

            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
            # Check if the time off type requires a support document
            time_off_type = request.env['hr.leave.type'].browse(time_off_type_id)
            if getattr(time_off_type, 'support_document', False) and not supported_attachment_ids:
                raise exceptions.ValidationError(f"Support document is required for {time_off_type.name} leave type")
            
            # Validate attachment data structure and limit
            if supported_attachment_ids:
                if not isinstance(supported_attachment_ids, list):
                    raise exceptions.ValidationError("supported_attachment_ids must be a list")
                
                # No file size or quantity limits - open for all attachments
                
                # Validate each attachment has required fields (no file type restrictions)
                for i, attachment_data in enumerate(supported_attachment_ids):
                    if not isinstance(attachment_data, dict):
                        raise exceptions.ValidationError(f"Attachment {i+1} must be a dictionary")
                    if not attachment_data.get('datas'):
                        raise exceptions.ValidationError(f"Attachment {i+1} is missing 'datas' field")
                    if not attachment_data.get('name'):
                        raise exceptions.ValidationError(f"Attachment {i+1} is missing 'name' field")

            # Convert date_from and date_to to date objects for comparison
            date_from_dt = fields.Date.from_string(date_from)
            date_to_dt = fields.Date.from_string(date_to)

            # Check if there is an overlapping leave request for this employee
            overlapping_leave = request.env['hr.leave'].search([
                ('employee_id', '=', employee_id),
                ('state', 'in', ['confirm', 'validate']),  # Consider only confirmed or validated requests
                '|',
                '&', ('request_date_from', '<=', date_to), ('request_date_to', '>=', date_from),
                '&', ('request_date_from', '>=', date_from), ('request_date_from', '<=', date_to),
            ])

            if overlapping_leave:
                return {
                    "status": "error",
                    "message": f"Employee already has a time-off request from {overlapping_leave.request_date_from} to {overlapping_leave.request_date_to}."
                }

            # No overlapping time-off, proceed to create a new request
            time_off_request = request.env['hr.leave'].create({
                'employee_id': employee.id,
                'holiday_status_id': time_off_type_id,
                'request_date_from': date_from,
                'name': reason,
                'request_date_to': date_to,
            })

            # Handle support document attachments if provided
            if supported_attachment_ids:
                try:
                    # Prepare all attachment values for bulk creation
                    attachment_vals_list = []
                    for i, attachment_data in enumerate(supported_attachment_ids):
                        attachment_vals = {
                            'name': attachment_data.get('name', f'Support_Document_{time_off_type.name}_{time_off_request.id}_{i+1}'),
                            'type': 'binary',
                            'datas': attachment_data.get('datas'),
                            'res_model': 'hr.leave',
                            'res_id': time_off_request.id,
                            'mimetype': attachment_data.get('mimetype', 'application/pdf'),
                        }
                        attachment_vals_list.append(attachment_vals)
                    
                    # Bulk create all attachments at once for better performance
                    if attachment_vals_list:
                        request.env['ir.attachment'].create(attachment_vals_list)
                        _logger.info(f"Successfully created {len(attachment_vals_list)} support document attachments for time off request {time_off_request.id}")
                        
                except Exception as e:
                    _logger.error(f"Failed to create support document attachments: {str(e)}")
                    # Don't fail the entire request if attachments fail, but log the error
                    # You might want to raise an exception here depending on your business logic

            return {
                "status": "success",
                "time_off_request_id": time_off_request.id,
                "message": "Time off request created successfully"
            }

        except Exception as e:
            _logger.error(f"Failed to create time off request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


    @http.route('/api/employee/<int:employee_id>/time_off_requests', type='http', auth="user", methods=['GET'], csrf=False)
    def get_time_off_requests(self, employee_id, **params):
        try:
            # Search for time-off requests for the specified employee
            # time_off_requests = request.env['hr.leave'].search([('employee_id', '=', employee_id)])
            # time_off_requests = request.env['hr.leave'].search([
            #     ('employee_id', '=', employee_id) #,
            #    # ('state', 'in', ['validate', 'validate1'])  # keep only approved
            # ])
            limit = int(params.get('limit', 100))
            offset = int(params.get('offset', 0))

            time_off_requests = request.env['hr.leave'].search(
                [('employee_id', '=', employee_id)],
                order='id desc',
                limit=limit,
                offset=offset
            )

            def _get_status_name(status_value):
                status_mapping = {
                    'draft': 'تم الارسال',
                    'confirm': 'بانتظار الموافقة',
                    'validate': 'مقبولة',
                    'refuse': 'مرفوضة',
                    'cancel': 'ملغية',
                    'validate1': 'تمت الموافقة  من المستوى الأعلى',
                }
                return status_mapping.get(status_value, 'Unknown Status')

            # Prepare the response data with additional fields as requested
            time_off_requests_data = [{
                'time_off_request_id': time_off_request.id,
                'employee_id': time_off_request.employee_id.id,
                'employee_name': time_off_request.employee_id.name,
                'date_from': time_off_request.request_date_from.strftime('%Y-%m-%d') if time_off_request.request_date_from else None,
                'date_to': time_off_request.request_date_to.strftime('%Y-%m-%d') if time_off_request.request_date_to else None,
                'status': _get_status_name(time_off_request.state),
                'duration':time_off_request.duration_display,
                'time_off_type': time_off_request.holiday_status_id.name,
                'description': time_off_request.name,
                'date_created': time_off_request.create_date.strftime('%Y-%m-%d %H:%M:%S') if time_off_request.create_date else None
            } for time_off_request in time_off_requests]

            # Return the response as a proper JSON HTTP response
            return request.make_response(json.dumps({"time_off_requests": time_off_requests_data}), headers=[('Content-Type', 'application/json')])

        except Exception as e:
            _logger.error(f"Failed to fetch time off requests: {str(e)}")
            error_data = {'status': 'error', 'message': str(e)}
            return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])

    # Payslip generation with details
    @http.route('/api/employee/payslip', type='json', auth="user", methods=['POST'], csrf=False)
    def generate_payslip(self, **post):
        try:
            data = post.get('data', {})
            employee_id = data.get('employee_id')
            date_from = data.get('date_from')
            date_to = data.get('date_to')

            if not all([employee_id, date_from, date_to]):
                raise exceptions.ValidationError("employee_id, date_from, and date_to are required")

            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            payslip_data = {
                'employee_id': employee.id,
                'date_from': date_from,
                'date_to': date_to,
                'struct_id': employee.contract_id.struct_id.id if employee.contract_id else False,
                'contract_id': employee.contract_id.id if employee.contract_id else False,
            }

            payslip = request.env['hr.payslip'].create(payslip_data)
            payslip.compute_sheet()  # Compute the payslip

            payslip_structure_data = [{
                'name': line.name,
                'code': line.code,
                'quantity': line.quantity,
                'rate': line.rate,
                'amount': line.total
            } for line in payslip.line_ids]

            return {
                "payslip_id": payslip.id,
                "employee_id": payslip.employee_id.id,
                "date_from": payslip.date_from,
                "date_to": payslip.date_to,
                "amount_total": payslip.amount_total,
                "state": payslip.state,
                "payslip_structure": payslip_structure_data,
                "message": "Payslip generated successfully"
            }
        
        except Exception as e:
            _logger.error(f"Failed to generate payslip: {str(e)}")
            return error_response(e, str(e))

    # Get all payslip history by employee ID
    @http.route('/api/employee/<int:employee_id>/payslip_history', type='http', auth="user", methods=['GET'], csrf=False)
    def get_payslip_history(self, employee_id, **params):
        try:
            payslips = request.env['hr.payslip'].search([('employee_id', '=', employee_id)])

            # Prepare the payslip data
            payslip_data = []
            for payslip in payslips:
                # Calculate the total amount by summing line amounts, if applicable
                #total_amount = sum(line.total for line in payslip.line_ids if line.category_id.code == 'NET')  # Assuming 'NET' is the category for net wage

                payslip_data.append({
                    'payslip_id': payslip.id,
                    'patch':payslip.payslip_run_id.name,
                    'employee_id': payslip.employee_id.id,
                    'date_from': payslip.date_from.strftime('%Y-%m-%d') if payslip.date_from else None,
                    'date_to': payslip.date_to.strftime('%Y-%m-%d') if payslip.date_to else None,
                    'amount_total': payslip.net_wage,
                    'state': payslip.state
                })

            # Return the response as JSON
            return request.make_response(json.dumps({"payslip_history": payslip_data}), headers=[('Content-Type', 'application/json')])

        except Exception as e:
            _logger.error(f"Failed to fetch payslip history: {str(e)}")
            return request.make_response(json.dumps({'error': str(e)}), headers=[('Content-Type', 'application/json')])


    # Get contract details for employee
    @http.route('/api/employee/<int:employee_id>/contract', type='http', auth="user", methods=['GET'], csrf=False)
    def get_contract_details(self, employee_id, **params):
        try:
            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            if not employee.contract_id:
                raise exceptions.ValidationError("No contract found for the specified employee.")

            contract = employee.contract_id
            contract_data = {
                'contract_id': contract.id,
                'display_name':contract.display_name,
                'employee_id': contract.employee_id.id,
                'date_start': contract.date_start.strftime('%Y-%m-%d') if contract.date_start else None,
                'date_end': contract.date_end.strftime('%Y-%m-%d') if contract.date_end else None,
                'wage': contract.wage,
                'job_title': contract.job_id.name,
                'department': contract.department_id.name if contract.department_id else None,
                'working_hours': contract.resource_calendar_id.name if contract.resource_calendar_id else None
            }

            return request.make_response(json.dumps({"contract_details": contract_data}), headers=[('Content-Type', 'application/json')])

        except Exception as e:
            _logger.error(f"Failed to fetch contract details: {str(e)}")
            return request.make_response(json.dumps({'error': str(e)}), headers=[('Content-Type', 'application/json')])
    


    # @http.route('/api/expense/create', type='http', auth='user', methods=['POST'], csrf=False)
    # def create_expense_request(self, **kwargs):
    #     try:
    #         # Extract necessary parameters from the request
    #         employee_id = int(kwargs.get('employee_id'))
    #         product_id = int(kwargs.get('product_id'))
    #         description = kwargs.get('description', '')
    #         amount = float(kwargs.get('amount'))
    #         attachment_path = kwargs.get('attachment_path')

    #         # Find the employee and product records
    #         employee = request.env['hr.employee'].sudo().browse(employee_id)
    #         product = request.env['product.product'].sudo().browse(product_id)

    #         if not employee.exists() or not product.exists():
    #             return request.make_response(
    #                 json.dumps({'error': 'Employee or product not found'}),
    #                 headers=[('Content-Type', 'application/json')],
    #                 status=404
    #             )

    #         # Create the expense request
    #         expense_vals = {
    #             'employee_id': employee.id,
    #             'name': description,
    #             'product_id': product.id,
    #             'total_amount_currency': amount,
    #         }
    #         expense = request.env['hr.expense'].sudo().create(expense_vals)

    #         # Handle attachment if provided
    #         if attachment_path and os.path.exists(attachment_path):
    #             with open(attachment_path, 'rb') as file:
    #                 attachment_data = file.read()
    #                 attachment_base64 = base64.b64encode(attachment_data).decode('utf-8')

    #             attachment_vals = {
    #                 'name': os.path.basename(attachment_path),
    #                 'res_model': 'hr.expense',
    #                 'res_id': expense.id,
    #                 'type': 'binary',
    #                 'datas': attachment_base64,
    #             }
    #             request.env['ir.attachment'].sudo().create(attachment_vals)

    #         return request.make_response(
    #             json.dumps({'success': True, 'expense_id': expense.id}),
    #             headers=[('Content-Type', 'application/json')]
    #         )

    #     except Exception as e:
    #         return request.make_response(
    #             json.dumps({'error': str(e)}),
    #             headers=[('Content-Type', 'application/json')],
    #             status=500
    #         )


    @http.route('/api/expense/create', type='http', auth='user', methods=['POST'], csrf=False)
    def create_expense_request(self, **kwargs):
        try:
            # Extract necessary parameters from the request
            employee_id = int(kwargs.get('employee_id'))
            product_id = int(kwargs.get('product_id'))
            description = kwargs.get('description', '')
            amount = float(kwargs.get('amount'))
            user_id = int(kwargs.get('user_id'))  # Get the user ID
            attachment = request.httprequest.files.get('attachment')

            # Find the employee and product records
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            product = request.env['product.product'].sudo().browse(product_id)

            if not employee.exists() or not product.exists():
                return request.make_response(
                    json.dumps({'error': 'Employee or product not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Create the expense request
            expense_vals = {
                'employee_id': employee.id,
                'name': description,
                'product_id': product.id,
                'total_amount_currency': amount,
                'activity_user_id': user_id,  # Assign the user ID to activity user
                'description': description,
            }
            expense = request.env['hr.expense'].sudo().create(expense_vals)

            # Submit the expense for approval
            expense.action_submit_expenses()

            # Handle attachment if provided
            if attachment and attachment.filename:
                attachment_data = attachment.read()
                attachment_base64 = base64.b64encode(attachment_data).decode('utf-8')

                attachment_vals = {
                    'name': attachment.filename,
                    'res_model': 'hr.expense',
                    'res_id': expense.id,
                    'type': 'binary',
                    'datas': attachment_base64,
                }
                request.env['ir.attachment'].sudo().create(attachment_vals)

            # Gather expense data to include in response
            expense_sheet = expense.sheet_id
            expense_data = {
                'id': expense.id,
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'employee_name': expense.employee_id.name,
                'activity_user_id': expense.activity_user_id.id if expense.activity_user_id else None,
                'activity_user_name': expense.activity_user_id.name if expense.activity_user_id else None,
                'date': str(expense.date),  # Convert date to string to avoid serialization issues
                'unit_amount': expense.total_amount_currency,
                'product_id': expense.product_id.id,
                'product_name': expense.product_id.name,
                'description': expense.description,
                'state': expense.state,
                'sheet_id': expense_sheet.id if expense_sheet else None,
                'sheet_name': expense_sheet.name if expense_sheet else None,
                'sheet_state': expense_sheet.state if expense_sheet else None,
            }

            return request.make_response(
                json.dumps({'success': True, 'expense': expense_data}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )






    # Separate route for manager actions (e.g., approving the expense)
    @http.route('/api/manager/approve_expense', type='http', auth="user", methods=['POST'], csrf=False)
    def approve_expense(self, **params):
        try:
            # Get details from params or request body
            data = json.loads(request.httprequest.data)
            expense_id = data.get('expense_id')
            journal_id = data.get('journal_id')

            # Check if the current user has manager permissions
            if not request.env.user.has_group('hr_expense.group_hr_expense_manager'):
                return request.make_response(
                    json.dumps({'error': 'Access Denied: You do not have the required permissions to approve expenses.'}),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )

            # Retrieve the expense record
            expense = request.env['hr.expense'].sudo().browse(expense_id)
            if not expense.exists():
                return request.make_response(
                    json.dumps({'error': 'Expense not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Approve the expense
            expense.sheet_id.sudo().action_approve_expense_sheets()

            # Create a payment for the expense
            expense_sheet = expense.sheet_id
            payment_data = {
                'partner_type': 'supplier',  # Since this is a reimbursement to the employee
                'partner_id': expense.employee_id.user_id.partner_id.id,  # Employee's partner record (needs to be configured in employee)
                'amount': expense.total_amount_currency,
                'payment_type': 'outbound',
                'journal_id': journal_id,
                'payment_method_id': request.env.ref('account.account_payment_method_manual_out').id,
                'date': str(fields.Date.today()),  # Convert date to string to avoid serialization issues
                'ref': expense_sheet.name
            }
            payment = request.env['account.payment'].sudo().create(payment_data)

            # Post the payment
            payment.sudo().action_post()
            expense.sudo().write({'state': 'submitted'})
            # Prepare response data from hr.expense.sheet
            response_data = {
                'expense_id': expense.id,
                'expense_state': expense.state,
                'payment_id': payment.id,
                'payment_state': payment.state,
                'sheet_id': expense_sheet.id if expense_sheet else None,
                'sheet_name': expense_sheet.name if expense_sheet else None,
                'sheet_state': expense_sheet.state if expense_sheet else None,
            }

            return request.make_response(
                json.dumps({'success': True, 'data': response_data}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Failed to approve expense: {str(e)}")
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    # Route to get all expense products with images
    # @http.route('/api/expense/products', type='http', auth="user", methods=['GET'], csrf=False)
    # def get_expense_products_with_images(self, **params):
    #     try:
    #         # Retrieve all products related to expenses
    #         products = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])

    #         # Prepare product data with images
    #         product_list = []
    #         for product in products:
    #             product_data = {
    #                 'id': product.id,
    #                 'name': product.name,
    #                 'description': product.description_sale,
    #                  'image':get_image_url(product.image_1920, model_name='product.product')  if product.image_1920 else None

    #                 #'image': product.image_1920 if product.image_1920 else None
    #             }
    #             product_list.append(product_data)

    #         return request.make_response(
    #             json.dumps({'success': True, 'products': product_list}),
    #             headers=[('Content-Type', 'application/json')]
    #         )

    #     except Exception as e:
    #         _logger.error(f"Failed to retrieve expense products: {str(e)}")
    #         return request.make_response(
    #             json.dumps({'error': str(e)}),
    #             headers=[('Content-Type', 'application/json')],
    #             status=500
    #         )

    # @http.route('/api/expense/products', type='http', auth="public", methods=['GET'], csrf=False)
    # def get_expense_products_with_images(self, **params):
    #     try:
    #         # Retrieve all products related to expenses
    #         products = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])

    #         # Prepare product data with images
    #         product_list = []
    #         for product in products:
    #             product_data = {
    #                 'id': product.id,
    #                 'name': product.name,
    #                 'description': product.description_sale,
    #                 'image_url': get_image_url(product)  # Use the general function
    #             }
    #             product_list.append(product_data)

    #         return request.make_response(
    #             json.dumps({'success': True, 'products': product_list}),
    #             headers=[('Content-Type', 'application/json')]
    #         )

    #     except Exception as e:
    #         _logger.error(f"Failed to retrieve expense products: {str(e)}")
    #         return request.make_response(
    #             json.dumps({'error': str(e)}),
    #             headers=[('Content-Type', 'application/json')],
    #             status=500
    #         )
    @http.route('/api/expense/products', type='http', auth="public", methods=['GET'], csrf=False)
    def get_expense_products_with_images(self, **params):
        try:
            # Retrieve all products related to expenses
            products = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])

            # Prepare product data with images
            product_list = []
            for product in products:
                # Encode the image in Base64 format
                image_data = base64.b64encode(product.image_1920).decode('utf-8') if product.image_1920 else None
                
                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description_sale,
                    'image_base64': image_data  # Returning the image as a Base64-encoded string
                }
                product_list.append(product_data)

            return request.make_response(
                json.dumps({'success': True, 'products': product_list}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Failed to retrieve expense products: {str(e)}")
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    # Route to get expenses related to the current user by user_id or employee_id
    @http.route('/api/employee/my_expenses', type='http', auth="user", methods=['POST'], csrf=False)
    def get_my_expenses(self, **params):
        try:
            # Get details from params or request body
            data = json.loads(request.httprequest.data)
            user_id = data.get('user_id')
            employee_id = data.get('employee_id')

            if not user_id and not employee_id:
                return request.make_response(
                    json.dumps({'error': 'Missing required parameters: user_id or employee_id'}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            employee = None
            if employee_id:
                employee = request.env['hr.employee'].sudo().browse(employee_id)
            elif user_id:
                employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)

            if not employee or not employee.exists():
                return request.make_response(
                    json.dumps({'error': 'Employee not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Retrieve all expenses related to the employee
            expenses = request.env['hr.expense'].sudo().search([('employee_id', '=', employee.id)])

            # Prepare expense data
            expense_list = []
            for expense in expenses:
                expense_sheet = expense.sheet_id
                expense_data = {
                    'id': expense.id,
                    'name': expense.name,
                    'employee_id': expense.employee_id.id,
                    'employee_name': expense.employee_id.name,
                    'activity_user_id': expense.activity_user_id.id,
                    'activity_user_name': expense.activity_user_id.name,
                    'date': str(expense.date),
                    'unit_amount': expense.total_amount_currency,
                    'product_id': expense.product_id.id,
                    'product_name': expense.product_id.name,
                    'description': expense.description,
                    'state': expense.state,
                    'sheet_id': expense_sheet.id if expense_sheet else None,
                    'sheet_name': expense_sheet.name if expense_sheet else None,
                    'sheet_state': expense_sheet.state if expense_sheet else None,
                }
                expense_list.append(expense_data)

            return request.make_response(
                json.dumps({'success': True, 'expenses': expense_list}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Failed to retrieve expenses for the current user: {str(e)}")
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    # Update employee PIN
    @http.route('/api/employee/<int:employee_id>/pin', type='json', auth="user", methods=['PUT'], csrf=False)
    def update_employee_pin(self, employee_id, **post):
        try:
            data = post.get('data', {})
            new_pin = data.get('pin')
            
            if not employee_id:
                raise exceptions.ValidationError("employee_id is required")
            
            if not new_pin:
                raise exceptions.ValidationError("PIN is required")
            
            # Validate PIN format (assuming numeric PIN)
            if not str(new_pin).isdigit():
                raise exceptions.ValidationError("PIN must contain only numbers")
            
            # Check PIN length (adjust as per your requirements)
            if len(str(new_pin)) < 4 or len(str(new_pin)) > 10:
                raise exceptions.ValidationError("PIN must be between 4 and 10 digits")
            
            # Get the employee
            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
            # Check if PIN is already used by another employee
            existing_employee = request.env['hr.employee'].search([
                ('pin', '=', new_pin),
                ('id', '!=', employee_id)
            ])
            
            if existing_employee:
                raise exceptions.ValidationError(f"PIN {new_pin} is already used by another employee")
            
            # Update the PIN
            old_pin = employee.pin
            employee.write({'pin': new_pin})
            
            # Log the PIN change
            employee.message_post(
                body=f"Employee PIN updated from {old_pin or 'None'} to {new_pin}",
                subtype_xmlid="mail.mt_note",
                message_type='comment'
            )
            
            response_data = {
                'status': 'success',
                'message': 'Employee PIN updated successfully',
                'employee_id': employee_id,
                'old_pin': old_pin,
                'new_pin': new_pin
            }
            
            return response_data
            
        except Exception as e:
            _logger.error(f"Failed to update employee PIN: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    # Get employee PIN
    @http.route('/api/employee/<int:employee_id>/pin', type='http', auth="user", methods=['GET'], csrf=False)
    def get_employee_pin(self, employee_id):
        try:
            if not employee_id:
                raise exceptions.ValidationError("employee_id is required")
            
            # Get the employee
            employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
            response_data = {
                'status': 'success',
                'employee_id': employee_id,
                'employee_name': employee.name,
                'pin': employee.pin,
                'has_pin': bool(employee.pin)
            }
            
            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.error(f"Failed to get employee PIN: {str(e)}")
            error_data = {
                'status': 'error',
                'message': str(e)
            }
            return request.make_response(
                json.dumps(error_data),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
            
            

# from odoo import http, fields, models, exceptions, _
# from odoo.http import request
# from datetime import datetime
# from datetime import timedelta
# from werkzeug.wrappers import Response
# from markupsafe import Markup
# import pytz
# import logging
# import json
# import base64


# _logger = logging.getLogger(__name__)

# def error_response(exception, message):
#     return {
#         "error": {
#             "type": type(exception).__name__,
#             "message": message
#         }
#     }
# def get_image_url(record, image_field='image_1920'):
#     """
#     Generates a URL for the image of a given record.
#     This function can be used across all Odoo modules.

#     Args:
#         record (Record): The Odoo record for which the image URL should be generated.
#         image_field (str): The field name of the image, default is 'image_1920'.

#     Returns:
#         str: The URL to access the image or None if the image doesn't exist.
#     """
#     if hasattr(record, image_field) and getattr(record, image_field):
#         # Correcting the model name encoding issue by ensuring proper formatting
#         model_name = record._name.replace('.', '%2E')
#         image_route = f'/web/image/{model_name}/{record.id}/{image_field}'
#         return request.httprequest.host_url.rstrip('/') + '/' + image_route
#     else:
#         return None

   
   
# def format_datetime(dt, tz_name='Africa/Cairo'):
#     """Format datetime to a string in ISO 8601 format and convert to local timezone."""
#     if not dt or isinstance(dt, bool):  # Handle None or False values gracefully
#         return None
#     tz = pytz.timezone(tz_name)
#     local_dt = dt.astimezone(tz)
#     return local_dt.strftime("%Y-%m-%dT%H:%M:%S")


# def format_datetime(dt, tz_name='Africa/Cairo'):
#     """Format datetime to a string in ISO 8601 format and convert to local timezone."""
#     if not dt or isinstance(dt, bool):  # Handle None or False values gracefully
#         return None
#     tz = pytz.timezone(tz_name)
#     local_dt = dt.astimezone(tz)
#     return local_dt.strftime("%Y-%m-%dT%H:%M:%S")

# def convert_decimal_to_time(decimal_hours):
#     """Convert a decimal representation of hours into HH:MM format."""
#     if decimal_hours is None:
#         return None
#     hours = int(decimal_hours)
#     minutes = int((decimal_hours - hours) * 60)
#     return f"{hours:02}:{minutes:02}"
# def post_map_link(record, latitude, longitude, address):
#         link = f"https://maps.google.com/maps?q={latitude},{longitude}&z=18"
#         map_link = f'<a href="{link}" target="_blank" rel="noreferrer noopener">{link}   </a>'
#         record.message_post(
#             body=Markup(map_link),  # Directly using the map link without wrapping in any additional tags
#             subtype_xmlid="mail.mt_note",
#             message_type='comment'  # Ensuring the message is treated as a comment
#         )  
# class EmployeeHRFunctions(http.Controller):
    
#     # Attendance with geolocation and timestamp for check-in and check-out
#     @http.route('/api/employee/attendance', type='json', auth="user", methods=['POST'], csrf=False)
#     def register_attendance(self, **post):
#         try:
#             data = post.get('data', {})
#             employee_id = data.get('employee_id')
#             latitude = data.get('latitude')
#             longitude = data.get('longitude')
#             ip = data.get('ip')
#             address_id = data.get('address_id')
#             country = data.get('country')
#             city= data.get('city')
#             action = data.get('action')  # Either 'check_in' or 'check_out'
#             timestamp = fields.Datetime.now()

#             if not employee_id:
#                 raise exceptions.ValidationError("employee_id is required")
#             if not action or action not in ['check_in', 'check_out']:
#                 raise exceptions.ValidationError("action must be either 'check_in' or 'check_out'")

#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()
#             attendance = request.env['hr.attendance'].search([('employee_id', '=', employee.id), ('check_out', '=', False)], limit=1)

#             if action == 'check_in':
#                 if attendance:
#                     raise exceptions.ValidationError("Employee is already checked in. Please check out first.")
                
#                 attendance = request.env['hr.attendance'].create({
#                     'employee_id': employee.id,
#                     'check_in': timestamp,
#                     'in_latitude': latitude,
#                     'in_longitude': longitude,
#                     'in_mode':'manual',
#                     'in_browser':'mobile app',
#                     'in_ip_address':ip,
#                     'in_country_name':country,
#                      "in_city":city,
#                      'address_id':address_id
#                 })
#                 message = "Check-in recorded successfully"
#                 post_map_link(attendance, latitude, longitude, address_id)
#             else:  # action == 'check_out'
#                 # First, check if there's a checkout record from today to update
#                 today = fields.Date.today()
#                 last_checkout_today = request.env['hr.attendance'].search([
#                     ('employee_id', '=', employee.id),
#                     ('check_out', '!=', False),
#                     ('check_out', '>=', today),
#                     ('check_out', '<', today + timedelta(days=1))
#                 ], order='check_out desc', limit=1)
                
#                 if last_checkout_today:
#                     # Update the last checkout record from today with new data from API
#                     last_checkout_today.write({
#                         'check_out': timestamp,
#                         'out_latitude': latitude,
#                         'out_longitude': longitude,
#                         'out_mode': 'manual',
#                         'out_browser': 'mobile app',
#                         'out_ip_address': ip,
#                         'out_country_name': country,
#                         "out_city": city
#                     })
#                     _logger.info(f"Updated last checkout record for employee {employee.id} from today")
#                     message = "Last checkout record updated successfully"
#                     post_map_link(last_checkout_today, latitude, longitude, address_id)
#                     attendance = last_checkout_today  # Set attendance for return value
#                 else:
#                     # If no checkout record from today exists, check for active check-in
#                     if not attendance:
#                         raise exceptions.ValidationError("No active check-in found for the employee. Please check in first.")
                    
#                     # Update the current attendance with checkout information
#                     attendance.write({
#                         'check_out': timestamp,
#                         'out_latitude': latitude,
#                         'out_longitude': longitude,
#                         'out_mode': 'manual',
#                         'out_browser': 'mobile app',
#                         'out_ip_address': ip,
#                         'out_country_name': country,
#                         "out_city": city
#                     })
#                     message = "Check-out recorded successfully"
#                     post_map_link(attendance, latitude, longitude, address_id)
#             return {"attendance_id": attendance.id, "message": message}
        
#         except Exception as e:
#             _logger.error(f"Failed to register attendance: {str(e)}")
#             return error_response(e, str(e))
        
        
    
#     @http.route('/api/employee/<int:employee_id>/attendances', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_attendance_records(self, employee_id, **params):
#         try:
#             attendances = request.env['hr.attendance'].search([('employee_id', '=', employee_id)])

#             # Initialize an empty list to collect attendance data
#             attendance_data = []


#             # Iterate over each attendance record and prepare the response data
#             for attendance in attendances:
#                 attendance_record = {
#                     'attendance_id': attendance.id,
#                     'employee_id': attendance.employee_id.id,
#                     'employee_name': attendance.employee_id.name,
#                     'check_in': format_datetime(attendance.check_in),
#                     'check_out': format_datetime(attendance.check_out),
#                     'worked_hours': convert_decimal_to_time(attendance.worked_hours),
#                     'overtime_hours': convert_decimal_to_time(attendance.overtime_hours),
#                     "in_latitude": attendance.in_latitude,
#                     "in_longitude": attendance.in_longitude,
#                     "in_country_name": attendance.in_country_name,
#                     "in_city": attendance.in_city,
#                     "in_browser": attendance.in_browser,
#                     "out_latitude": attendance.out_latitude,
#                     "out_longitude": attendance.out_longitude,
#                     "out_country_name": attendance.out_country_name,
#                     "out_city": attendance.out_city,
#                     "out_browser": attendance.out_browser
                  
#                 }
#                 # Add the record to the list
#                 attendance_data.append(attendance_record)

#             response_data = {"attendances": attendance_data}

#             # Use request.make_response to create an HTTP response with the proper JSON formatting
#             return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

#         except Exception as e:
#             _logger.error(f"Failed to fetch attendance records: {str(e)}")
#             error_data = {
#                 'status': 'error',
#                 'message': str(e)
#             }
#             return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])






































#     @http.route('/api/employee/<int:employee_id>/last_attendance_status', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_last_attendance_with_status(self, employee_id, **params):
#         try: 
#             # Retrieve the employee record
#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()

#             if not employee:
#                 raise exceptions.ValidationError("Invalid employee ID")

#             # Retrieve the last attendance record for the employee
#             last_attendance = request.env['hr.attendance'].search([('employee_id', '=', employee.id)], order='check_in desc', limit=1)

#             if not last_attendance:
#                 # No attendance records found for this employee
#                 response_data = {
#                     'status': 'success',
#                     'message': 'No attendance records found for this employee',
#                     'last_attendance': None
#                 }
#             else:
#                 # Determine the status based on whether check_out is present
#                 attendance_status = "check-in" if not last_attendance.check_out else "check-out"
#                 def convert_decimal_to_time(decimal_hours):
#                     """Convert a decimal representation of hours into HH:MM format."""
#                     if decimal_hours is None:
#                         return None
#                     # Split the hours and minutes
#                     hours = int(decimal_hours)  # Get the integer part as hours
#                     minutes = int((decimal_hours - hours) * 60)  # Get the fractional part and convert it to minutes
#                     return f"{hours:02}:{minutes:02}"
            
#                 # Create response data for the last attendance
#                 last_attendance_data = {
#                     'attendance_id': last_attendance.id,
#                     'employee_id': last_attendance.employee_id.id,
#                     'employee_name': last_attendance.employee_id.name,
#                     'check_in': format_datetime(last_attendance.check_in) if last_attendance.check_in else None,
#                     'check_out': format_datetime(last_attendance.check_out) if last_attendance.check_out else None,
#                     'worked_hours': convert_decimal_to_time(last_attendance.worked_hours),
#                     "overtime_hours":convert_decimal_to_time(last_attendance.overtime_hours) ,
#                     "in_latitude": last_attendance.in_latitude,
#                     "in_longitude": last_attendance.in_longitude,
#                     "in_country_name": last_attendance.in_country_name,
#                     "in_city": last_attendance.in_city,
#                     "in_browser": last_attendance.in_browser,
#                     "out_latitude": last_attendance.out_latitude,
#                     "out_longitude": last_attendance.out_longitude,
#                     "out_country_name": last_attendance.out_country_name,
#                     "out_city": last_attendance.out_city,
#                     "out_browser": last_attendance.out_browser,
#                     "status": attendance_status  # Added status indicating check-in or check-out
#                 }

#                 response_data = {
#                     'status': 'success',
#                     'last_attendance': last_attendance_data
#                 }

#             # Use request.make_response to return a proper JSON HTTP response
#             return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

#         except Exception as e:
#             _logger.error(f"Failed to fetch last attendance with status: {str(e)}")
#             error_data = {
#                 'status': 'error',
#                 'message': str(e)
#             }
#             return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])


# #time_off_balance

#     @http.route('/api/employee/<int:employee_id>/time_off_balance', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_time_off_balance(self, employee_id, **params):
#         try:
#             if not employee_id:
#                 raise exceptions.ValidationError("employee_id is required")

#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
#             # Get allocation_status parameter from URL (default: 'all')
#             allocation_status = params.get('allocation_status', 'all').lower()
            
#             # Validate allocation_status parameter
#             valid_statuses = ['all', 'with_allocation', 'without_allocation']
#             if allocation_status not in valid_statuses:
#                 raise exceptions.ValidationError(f"Invalid allocation_status. Must be one of: {', '.join(valid_statuses)}")

#             balances = []
            
#             if allocation_status in ['all', 'with_allocation']:
#                 # Retrieve leave allocations for the employee
#                 allocations = request.env['hr.leave.allocation'].search([('employee_id', '=', employee.id), ('state', '=', 'validate')])

#                 for allocation in allocations:
#                     # Retrieve leave requests of the employee for the same leave type to calculate used days
#                     leave_requests = request.env['hr.leave'].search([
#                         ('employee_id', '=', employee.id),
#                         ('holiday_status_id', '=', allocation.holiday_status_id.id),
#                         ('state', 'in', ['confirm', 'validate'])
#                     ])
                    
#                     used_days = sum(leave.number_of_days for leave in leave_requests)
#                     remaining_days = allocation.number_of_days - used_days

#                     balances.append({
#                         'time_off_id': allocation.holiday_status_id.id,
#                         'time_off_type': allocation.holiday_status_id.name,
#                         'allocated_days': allocation.number_of_days,
#                         'remaining_days': remaining_days,
#                         'used_days': used_days,
#                         'has_allocation': True,
#                     })
            
#             if allocation_status in ['all', 'without_allocation']:
#                 # Get all leave types that have no allocation for the entire company
#                 # First, get all leave types in the system
#                 all_leave_types = request.env['hr.leave.type'].search([])
                
#                 # Get all allocated leave types for the entire company
#                 company_allocated_leave_types = request.env['hr.leave.allocation'].search([
#                     ('employee_id.company_id', '=', employee.company_id.id),
#                     ('state', '=', 'validate')
#                 ]).mapped('holiday_status_id')
                
#                 # Find leave types without any allocation in the company
#                 leave_types_without_allocation = all_leave_types - company_allocated_leave_types
                
#                 for leave_type in leave_types_without_allocation:
#                     # Calculate used days for this leave type by the specific employee
#                     leave_requests = request.env['hr.leave'].search([
#                         ('employee_id', '=', employee.id),
#                         ('holiday_status_id', '=', leave_type.id),
#                         ('state', 'in', ['confirm', 'validate'])
#                     ])
                    
#                     used_days = sum(leave.number_of_days for leave in leave_requests)

#                     balances.append({
#                         'time_off_id': leave_type.id,
#                         'time_off_type': leave_type.name,
#                         'allocated_days': 0,
#                         'remaining_days': 0,
#                         'used_days': used_days,
#                         'has_allocation': False,
#                     })

#             response_data = {
#                 'status': 'success',
#                 'time_off_balances': balances
#             }

#             # Use json_response to return a proper JSON HTTP response
#             return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

#         except Exception as e:
#             error_data = {
#                 'status': 'error',
#                 'message': str(e),
#             }
#             return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])


#         # Time off request
#     @http.route('/api/employee/time_off', type='json', auth="user", methods=['POST'], csrf=False)
#     def request_time_off(self, **post):
#         try:
#             data = post.get('data', {})
#             employee_id = data.get('employee_id')
#             reason = data.get('reason')
#             date_from = data.get('date_from')
#             date_to = data.get('date_to')
#             time_off_type_id = data.get('time_off_type_id')

#             if not all([employee_id, date_from, date_to, time_off_type_id]):
#                 raise exceptions.ValidationError("employee_id, date_from, date_to, and time_off_type_id are required")

#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()

#             # Convert date_from and date_to to date objects for comparison
#             date_from_dt = fields.Date.from_string(date_from)
#             date_to_dt = fields.Date.from_string(date_to)

#             # Check if there is an overlapping leave request for this employee
#             overlapping_leave = request.env['hr.leave'].search([
#                 ('employee_id', '=', employee_id),
#                 ('state', 'in', ['confirm', 'validate']),  # Consider only confirmed or validated requests
#                 '|',
#                 '&', ('request_date_from', '<=', date_to), ('request_date_to', '>=', date_from),
#                 '&', ('request_date_from', '>=', date_from), ('request_date_from', '<=', date_to),
#             ])

#             if overlapping_leave:
#                 return {
#                     "status": "error",
#                     "message": f"Employee already has a time-off request from {overlapping_leave.request_date_from} to {overlapping_leave.request_date_to}."
#                 }

#             # No overlapping time-off, proceed to create a new request
#             time_off_request = request.env['hr.leave'].create({
#                 'employee_id': employee.id,
#                 'holiday_status_id': time_off_type_id,
#                 'request_date_from': date_from,
#                 'name': reason,
#                 'request_date_to': date_to,
#             })

#             return {
#                 "status": "success",
#                 "time_off_request_id": time_off_request.id,
#                 "message": "Time off request created successfully"
#             }

#         except Exception as e:
#             _logger.error(f"Failed to create time off request: {str(e)}")
#             return {
#                 "status": "error",
#                 "message": str(e)
#             }


#     @http.route('/api/employee/<int:employee_id>/time_off_requests', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_time_off_requests(self, employee_id, **params):
#         try:
#             # Search for time-off requests for the specified employee
#             # time_off_requests = request.env['hr.leave'].search([('employee_id', '=', employee_id)])
#             # time_off_requests = request.env['hr.leave'].search([
#             #     ('employee_id', '=', employee_id) #,
#             #    # ('state', 'in', ['validate', 'validate1'])  # keep only approved
#             # ])
#             limit = int(params.get('limit', 100))
#             offset = int(params.get('offset', 0))

#             time_off_requests = request.env['hr.leave'].search(
#                 [('employee_id', '=', employee_id)],
#                 order='id desc',
#                 limit=limit,
#                 offset=offset
#             )

#             def _get_status_name(status_value):
#                 status_mapping = {
#                     'draft': 'تم الارسال',
#                     'confirm': 'بانتظار الموافقة',
#                     'validate': 'مقبولة',
#                     'refuse': 'مرفوضة',
#                     'cancel': 'ملغية',
#                     'validate1': 'تمت الموافقة  من المستوى الأعلى',
#                 }
#                 return status_mapping.get(status_value, 'Unknown Status')

#             # Prepare the response data with additional fields as requested
#             time_off_requests_data = [{
#                 'time_off_request_id': time_off_request.id,
#                 'employee_id': time_off_request.employee_id.id,
#                 'employee_name': time_off_request.employee_id.name,
#                 'date_from': time_off_request.request_date_from.strftime('%Y-%m-%d') if time_off_request.request_date_from else None,
#                 'date_to': time_off_request.request_date_to.strftime('%Y-%m-%d') if time_off_request.request_date_to else None,
#                 'status': _get_status_name(time_off_request.state),
#                 'duration':time_off_request.duration_display,
#                 'time_off_type': time_off_request.holiday_status_id.name,
#                 'description': time_off_request.name,
#                 'date_created': time_off_request.create_date.strftime('%Y-%m-%d %H:%M:%S') if time_off_request.create_date else None
#             } for time_off_request in time_off_requests]

#             # Return the response as a proper JSON HTTP response
#             return request.make_response(json.dumps({"time_off_requests": time_off_requests_data}), headers=[('Content-Type', 'application/json')])

#         except Exception as e:
#             _logger.error(f"Failed to fetch time off requests: {str(e)}")
#             error_data = {'status': 'error', 'message': str(e)}
#             return request.make_response(json.dumps(error_data), headers=[('Content-Type', 'application/json')])

#     # Payslip generation with details
#     @http.route('/api/employee/payslip', type='json', auth="user", methods=['POST'], csrf=False)
#     def generate_payslip(self, **post):
#         try:
#             data = post.get('data', {})
#             employee_id = data.get('employee_id')
#             date_from = data.get('date_from')
#             date_to = data.get('date_to')

#             if not all([employee_id, date_from, date_to]):
#                 raise exceptions.ValidationError("employee_id, date_from, and date_to are required")

#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()
#             payslip_data = {
#                 'employee_id': employee.id,
#                 'date_from': date_from,
#                 'date_to': date_to,
#                 'struct_id': employee.contract_id.struct_id.id if employee.contract_id else False,
#                 'contract_id': employee.contract_id.id if employee.contract_id else False,
#             }

#             payslip = request.env['hr.payslip'].create(payslip_data)
#             payslip.compute_sheet()  # Compute the payslip

#             payslip_structure_data = [{
#                 'name': line.name,
#                 'code': line.code,
#                 'quantity': line.quantity,
#                 'rate': line.rate,
#                 'amount': line.total
#             } for line in payslip.line_ids]

#             return {
#                 "payslip_id": payslip.id,
#                 "employee_id": payslip.employee_id.id,
#                 "date_from": payslip.date_from,
#                 "date_to": payslip.date_to,
#                 "amount_total": payslip.amount_total,
#                 "state": payslip.state,
#                 "payslip_structure": payslip_structure_data,
#                 "message": "Payslip generated successfully"
#             }
        
#         except Exception as e:
#             _logger.error(f"Failed to generate payslip: {str(e)}")
#             return error_response(e, str(e))

#     # Get all payslip history by employee ID
#     @http.route('/api/employee/<int:employee_id>/payslip_history', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_payslip_history(self, employee_id, **params):
#         try:
#             payslips = request.env['hr.payslip'].search([('employee_id', '=', employee_id)])

#             # Prepare the payslip data
#             payslip_data = []
#             for payslip in payslips:
#                 # Calculate the total amount by summing line amounts, if applicable
#                 #total_amount = sum(line.total for line in payslip.line_ids if line.category_id.code == 'NET')  # Assuming 'NET' is the category for net wage

#                 payslip_data.append({
#                     'payslip_id': payslip.id,
#                     'patch':payslip.payslip_run_id.name,
#                     'employee_id': payslip.employee_id.id,
#                     'date_from': payslip.date_from.strftime('%Y-%m-%d') if payslip.date_from else None,
#                     'date_to': payslip.date_to.strftime('%Y-%m-%d') if payslip.date_to else None,
#                     'amount_total': payslip.net_wage,
#                     'state': payslip.state
#                 })

#             # Return the response as JSON
#             return request.make_response(json.dumps({"payslip_history": payslip_data}), headers=[('Content-Type', 'application/json')])

#         except Exception as e:
#             _logger.error(f"Failed to fetch payslip history: {str(e)}")
#             return request.make_response(json.dumps({'error': str(e)}), headers=[('Content-Type', 'application/json')])


#     # Get contract details for employee
#     @http.route('/api/employee/<int:employee_id>/contract', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_contract_details(self, employee_id, **params):
#         try:
#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()
#             if not employee.contract_id:
#                 raise exceptions.ValidationError("No contract found for the specified employee.")

#             contract = employee.contract_id
#             contract_data = {
#                 'contract_id': contract.id,
#                 'display_name':contract.display_name,
#                 'employee_id': contract.employee_id.id,
#                 'date_start': contract.date_start.strftime('%Y-%m-%d') if contract.date_start else None,
#                 'date_end': contract.date_end.strftime('%Y-%m-%d') if contract.date_end else None,
#                 'wage': contract.wage,
#                 'job_title': contract.job_id.name,
#                 'department': contract.department_id.name if contract.department_id else None,
#                 'working_hours': contract.resource_calendar_id.name if contract.resource_calendar_id else None
#             }

#             return request.make_response(json.dumps({"contract_details": contract_data}), headers=[('Content-Type', 'application/json')])

#         except Exception as e:
#             _logger.error(f"Failed to fetch contract details: {str(e)}")
#             return request.make_response(json.dumps({'error': str(e)}), headers=[('Content-Type', 'application/json')])
    


#     # @http.route('/api/expense/create', type='http', auth='user', methods=['POST'], csrf=False)
#     # def create_expense_request(self, **kwargs):
#     #     try:
#     #         # Extract necessary parameters from the request
#     #         employee_id = int(kwargs.get('employee_id'))
#     #         product_id = int(kwargs.get('product_id'))
#     #         description = kwargs.get('description', '')
#     #         amount = float(kwargs.get('amount'))
#     #         attachment_path = kwargs.get('attachment_path')

#     #         # Find the employee and product records
#     #         employee = request.env['hr.employee'].sudo().browse(employee_id)
#     #         product = request.env['product.product'].sudo().browse(product_id)

#     #         if not employee.exists() or not product.exists():
#     #             return request.make_response(
#     #                 json.dumps({'error': 'Employee or product not found'}),
#     #                 headers=[('Content-Type', 'application/json')],
#     #                 status=404
#     #             )

#     #         # Create the expense request
#     #         expense_vals = {
#     #             'employee_id': employee.id,
#     #             'name': description,
#     #             'product_id': product.id,
#     #             'total_amount_currency': amount,
#     #         }
#     #         expense = request.env['hr.expense'].sudo().create(expense_vals)

#     #         # Handle attachment if provided
#     #         if attachment_path and os.path.exists(attachment_path):
#     #             with open(attachment_path, 'rb') as file:
#     #                 attachment_data = file.read()
#     #                 attachment_base64 = base64.b64encode(attachment_data).decode('utf-8')

#     #             attachment_vals = {
#     #                 'name': os.path.basename(attachment_path),
#     #                 'res_model': 'hr.expense',
#     #                 'res_id': expense.id,
#     #                 'type': 'binary',
#     #                 'datas': attachment_base64,
#     #             }
#     #             request.env['ir.attachment'].sudo().create(attachment_vals)

#     #         return request.make_response(
#     #             json.dumps({'success': True, 'expense_id': expense.id}),
#     #             headers=[('Content-Type', 'application/json')]
#     #         )

#     #     except Exception as e:
#     #         return request.make_response(
#     #             json.dumps({'error': str(e)}),
#     #             headers=[('Content-Type', 'application/json')],
#     #             status=500
#     #         )


#     @http.route('/api/expense/create', type='http', auth='user', methods=['POST'], csrf=False)
#     def create_expense_request(self, **kwargs):
#         try:
#             # Extract necessary parameters from the request
#             employee_id = int(kwargs.get('employee_id'))
#             product_id = int(kwargs.get('product_id'))
#             description = kwargs.get('description', '')
#             amount = float(kwargs.get('amount'))
#             user_id = int(kwargs.get('user_id'))  # Get the user ID
#             attachment = request.httprequest.files.get('attachment')

#             # Find the employee and product records
#             employee = request.env['hr.employee'].sudo().browse(employee_id)
#             product = request.env['product.product'].sudo().browse(product_id)

#             if not employee.exists() or not product.exists():
#                 return request.make_response(
#                     json.dumps({'error': 'Employee or product not found'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=404
#                 )

#             # Create the expense request
#             expense_vals = {
#                 'employee_id': employee.id,
#                 'name': description,
#                 'product_id': product.id,
#                 'total_amount_currency': amount,
#                 'activity_user_id': user_id,  # Assign the user ID to activity user
#                 'description': description,
#             }
#             expense = request.env['hr.expense'].sudo().create(expense_vals)

#             # Submit the expense for approval
#             expense.action_submit_expenses()

#             # Handle attachment if provided
#             if attachment and attachment.filename:
#                 attachment_data = attachment.read()
#                 attachment_base64 = base64.b64encode(attachment_data).decode('utf-8')

#                 attachment_vals = {
#                     'name': attachment.filename,
#                     'res_model': 'hr.expense',
#                     'res_id': expense.id,
#                     'type': 'binary',
#                     'datas': attachment_base64,
#                 }
#                 request.env['ir.attachment'].sudo().create(attachment_vals)

#             # Gather expense data to include in response
#             expense_sheet = expense.sheet_id
#             expense_data = {
#                 'id': expense.id,
#                 'name': expense.name,
#                 'employee_id': expense.employee_id.id,
#                 'employee_name': expense.employee_id.name,
#                 'activity_user_id': expense.activity_user_id.id if expense.activity_user_id else None,
#                 'activity_user_name': expense.activity_user_id.name if expense.activity_user_id else None,
#                 'date': str(expense.date),  # Convert date to string to avoid serialization issues
#                 'unit_amount': expense.total_amount_currency,
#                 'product_id': expense.product_id.id,
#                 'product_name': expense.product_id.name,
#                 'description': expense.description,
#                 'state': expense.state,
#                 'sheet_id': expense_sheet.id if expense_sheet else None,
#                 'sheet_name': expense_sheet.name if expense_sheet else None,
#                 'sheet_state': expense_sheet.state if expense_sheet else None,
#             }

#             return request.make_response(
#                 json.dumps({'success': True, 'expense': expense_data}),
#                 headers=[('Content-Type', 'application/json')]
#             )

#         except Exception as e:
#             return request.make_response(
#                 json.dumps({'error': str(e)}),
#                 headers=[('Content-Type', 'application/json')],
#                 status=500
#             )






#     # Separate route for manager actions (e.g., approving the expense)
#     @http.route('/api/manager/approve_expense', type='http', auth="user", methods=['POST'], csrf=False)
#     def approve_expense(self, **params):
#         try:
#             # Get details from params or request body
#             data = json.loads(request.httprequest.data)
#             expense_id = data.get('expense_id')
#             journal_id = data.get('journal_id')

#             # Check if the current user has manager permissions
#             if not request.env.user.has_group('hr_expense.group_hr_expense_manager'):
#                 return request.make_response(
#                     json.dumps({'error': 'Access Denied: You do not have the required permissions to approve expenses.'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=403
#                 )

#             # Retrieve the expense record
#             expense = request.env['hr.expense'].sudo().browse(expense_id)
#             if not expense.exists():
#                 return request.make_response(
#                     json.dumps({'error': 'Expense not found'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=404
#                 )

#             # Approve the expense
#             expense.sheet_id.sudo().action_approve_expense_sheets()

#             # Create a payment for the expense
#             expense_sheet = expense.sheet_id
#             payment_data = {
#                 'partner_type': 'supplier',  # Since this is a reimbursement to the employee
#                 'partner_id': expense.employee_id.user_id.partner_id.id,  # Employee's partner record (needs to be configured in employee)
#                 'amount': expense.total_amount_currency,
#                 'payment_type': 'outbound',
#                 'journal_id': journal_id,
#                 'payment_method_id': request.env.ref('account.account_payment_method_manual_out').id,
#                 'date': str(fields.Date.today()),  # Convert date to string to avoid serialization issues
#                 'ref': expense_sheet.name
#             }
#             payment = request.env['account.payment'].sudo().create(payment_data)

#             # Post the payment
#             payment.sudo().action_post()
#             expense.sudo().write({'state': 'submitted'})
#             # Prepare response data from hr.expense.sheet
#             response_data = {
#                 'expense_id': expense.id,
#                 'expense_state': expense.state,
#                 'payment_id': payment.id,
#                 'payment_state': payment.state,
#                 'sheet_id': expense_sheet.id if expense_sheet else None,
#                 'sheet_name': expense_sheet.name if expense_sheet else None,
#                 'sheet_state': expense_sheet.state if expense_sheet else None,
#             }

#             return request.make_response(
#                 json.dumps({'success': True, 'data': response_data}),
#                 headers=[('Content-Type', 'application/json')]
#             )

#         except Exception as e:
#             _logger.error(f"Failed to approve expense: {str(e)}")
#             return request.make_response(
#                 json.dumps({'error': str(e)}),
#                 headers=[('Content-Type', 'application/json')],
#                 status=500
#             )
#     # Route to get all expense products with images
#     # @http.route('/api/expense/products', type='http', auth="user", methods=['GET'], csrf=False)
#     # def get_expense_products_with_images(self, **params):
#     #     try:
#     #         # Retrieve all products related to expenses
#     #         products = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])

#     #         # Prepare product data with images
#     #         product_list = []
#     #         for product in products:
#     #             product_data = {
#     #                 'id': product.id,
#     #                 'name': product.name,
#     #                 'description': product.description_sale,
#     #                  'image':get_image_url(product.image_1920, model_name='product.product')  if product.image_1920 else None

#     #                 #'image': product.image_1920 if product.image_1920 else None
#     #             }
#     #             product_list.append(product_data)

#     #         return request.make_response(
#     #             json.dumps({'success': True, 'products': product_list}),
#     #             headers=[('Content-Type', 'application/json')]
#     #         )

#     #     except Exception as e:
#     #         _logger.error(f"Failed to retrieve expense products: {str(e)}")
#     #         return request.make_response(
#     #             json.dumps({'error': str(e)}),
#     #             headers=[('Content-Type', 'application/json')],
#     #             status=500
#     #         )

#     # @http.route('/api/expense/products', type='http', auth="public", methods=['GET'], csrf=False)
#     # def get_expense_products_with_images(self, **params):
#     #     try:
#     #         # Retrieve all products related to expenses
#     #         products = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])

#     #         # Prepare product data with images
#     #         product_list = []
#     #         for product in products:
#     #             product_data = {
#     #                 'id': product.id,
#     #                 'name': product.name,
#     #                 'description': product.description_sale,
#     #                 'image_url': get_image_url(product)  # Use the general function
#     #             }
#     #             product_list.append(product_data)

#     #         return request.make_response(
#     #             json.dumps({'success': True, 'products': product_list}),
#     #             headers=[('Content-Type', 'application/json')]
#     #         )

#     #     except Exception as e:
#     #         _logger.error(f"Failed to retrieve expense products: {str(e)}")
#     #         return request.make_response(
#     #             json.dumps({'error': str(e)}),
#     #             headers=[('Content-Type', 'application/json')],
#     #             status=500
#     #         )
#     @http.route('/api/expense/products', type='http', auth="public", methods=['GET'], csrf=False)
#     def get_expense_products_with_images(self, **params):
#         try:
#             # Retrieve all products related to expenses
#             products = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])

#             # Prepare product data with images
#             product_list = []
#             for product in products:
#                 # Encode the image in Base64 format
#                 image_data = base64.b64encode(product.image_1920).decode('utf-8') if product.image_1920 else None
                
#                 product_data = {
#                     'id': product.id,
#                     'name': product.name,
#                     'description': product.description_sale,
#                     'image_base64': image_data  # Returning the image as a Base64-encoded string
#                 }
#                 product_list.append(product_data)

#             return request.make_response(
#                 json.dumps({'success': True, 'products': product_list}),
#                 headers=[('Content-Type', 'application/json')]
#             )

#         except Exception as e:
#             _logger.error(f"Failed to retrieve expense products: {str(e)}")
#             return request.make_response(
#                 json.dumps({'error': str(e)}),
#                 headers=[('Content-Type', 'application/json')],
#                 status=500
#             )
#     # Route to get expenses related to the current user by user_id or employee_id
#     @http.route('/api/employee/my_expenses', type='http', auth="user", methods=['POST'], csrf=False)
#     def get_my_expenses(self, **params):
#         try:
#             # Get details from params or request body
#             data = json.loads(request.httprequest.data)
#             user_id = data.get('user_id')
#             employee_id = data.get('employee_id')

#             if not user_id and not employee_id:
#                 return request.make_response(
#                     json.dumps({'error': 'Missing required parameters: user_id or employee_id'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=400
#                 )

#             employee = None
#             if employee_id:
#                 employee = request.env['hr.employee'].sudo().browse(employee_id)
#             elif user_id:
#                 employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)

#             if not employee or not employee.exists():
#                 return request.make_response(
#                     json.dumps({'error': 'Employee not found'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=404
#                 )

#             # Retrieve all expenses related to the employee
#             expenses = request.env['hr.expense'].sudo().search([('employee_id', '=', employee.id)])

#             # Prepare expense data
#             expense_list = []
#             for expense in expenses:
#                 expense_sheet = expense.sheet_id
#                 expense_data = {
#                     'id': expense.id,
#                     'name': expense.name,
#                     'employee_id': expense.employee_id.id,
#                     'employee_name': expense.employee_id.name,
#                     'activity_user_id': expense.activity_user_id.id,
#                     'activity_user_name': expense.activity_user_id.name,
#                     'date': str(expense.date),
#                     'unit_amount': expense.total_amount_currency,
#                     'product_id': expense.product_id.id,
#                     'product_name': expense.product_id.name,
#                     'description': expense.description,
#                     'state': expense.state,
#                     'sheet_id': expense_sheet.id if expense_sheet else None,
#                     'sheet_name': expense_sheet.name if expense_sheet else None,
#                     'sheet_state': expense_sheet.state if expense_sheet else None,
#                 }
#                 expense_list.append(expense_data)

#             return request.make_response(
#                 json.dumps({'success': True, 'expenses': expense_list}),
#                 headers=[('Content-Type', 'application/json')]
#             )

#         except Exception as e:
#             _logger.error(f"Failed to retrieve expenses for the current user: {str(e)}")
#             return request.make_response(
#                 json.dumps({'error': str(e)}),
#                 headers=[('Content-Type', 'application/json')],
#                 status=500
#             )

#     # Update employee PIN
#     @http.route('/api/employee/<int:employee_id>/pin', type='json', auth="user", methods=['PUT'], csrf=False)
#     def update_employee_pin(self, employee_id, **post):
#         try:
#             data = post.get('data', {})
#             new_pin = data.get('pin')
            
#             if not employee_id:
#                 raise exceptions.ValidationError("employee_id is required")
            
#             if not new_pin:
#                 raise exceptions.ValidationError("PIN is required")
            
#             # Validate PIN format (assuming numeric PIN)
#             if not str(new_pin).isdigit():
#                 raise exceptions.ValidationError("PIN must contain only numbers")
            
#             # Check PIN length (adjust as per your requirements)
#             if len(str(new_pin)) < 4 or len(str(new_pin)) > 10:
#                 raise exceptions.ValidationError("PIN must be between 4 and 10 digits")
            
#             # Get the employee
#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
#             # Check if PIN is already used by another employee
#             existing_employee = request.env['hr.employee'].search([
#                 ('pin', '=', new_pin),
#                 ('id', '!=', employee_id)
#             ])
            
#             if existing_employee:
#                 raise exceptions.ValidationError(f"PIN {new_pin} is already used by another employee")
            
#             # Update the PIN
#             old_pin = employee.pin
#             employee.write({'pin': new_pin})
            
#             # Log the PIN change
#             employee.message_post(
#                 body=f"Employee PIN updated from {old_pin or 'None'} to {new_pin}",
#                 subtype_xmlid="mail.mt_note",
#                 message_type='comment'
#             )
            
#             response_data = {
#                 'status': 'success',
#                 'message': 'Employee PIN updated successfully',
#                 'employee_id': employee_id,
#                 'old_pin': old_pin,
#                 'new_pin': new_pin
#             }
            
#             return response_data
            
#         except Exception as e:
#             _logger.error(f"Failed to update employee PIN: {str(e)}")
#             return {
#                 'status': 'error',
#                 'message': str(e)
#             }

#     # Get employee PIN
#     @http.route('/api/employee/<int:employee_id>/pin', type='http', auth="user", methods=['GET'], csrf=False)
#     def get_employee_pin(self, employee_id):
#         try:
#             if not employee_id:
#                 raise exceptions.ValidationError("employee_id is required")
            
#             # Get the employee
#             employee = request.env['hr.employee'].browse(employee_id).ensure_one()
            
#             response_data = {
#                 'status': 'success',
#                 'employee_id': employee_id,
#                 'employee_name': employee.name,
#                 'pin': employee.pin,
#                 'has_pin': bool(employee.pin)
#             }
            
#             return request.make_response(
#                 json.dumps(response_data),
#                 headers=[('Content-Type', 'application/json')]
#             )
            
#         except Exception as e:
#             _logger.error(f"Failed to get employee PIN: {str(e)}")
#             error_data = {
#                 'status': 'error',
#                 'message': str(e)
#             }
#             return request.make_response(
#                 json.dumps(error_data),
#                 headers=[('Content-Type', 'application/json')],
#                 status=500
#             )
            
            
