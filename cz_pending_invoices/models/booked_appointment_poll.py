import logging
from datetime import datetime, timedelta

import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)


class BookedAppointmentPoll(models.Model):
    _name = 'cz.booked_appointment_poll'
    _description = 'Booked Appointment Poll'
    _sql_constraints = [('unique_date', 'UNIQUE(date)', 'Date must be unique')]

    date = fields.Date(string='Date')
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='new')

    def poll_yesterday(self):
        """Poll for booked appointments from yesterday"""
        yesterday = (datetime.today() - timedelta(days=1)).date()
        self.do_poll(yesterday)

    def poll_today(self):
        """Poll for booked appointments from today"""
        today = datetime.today().date()
        self.do_poll(today)

    def poll_custom_date(self, target_date):
        """Poll for booked appointments from a specific date
        
        Args:
            target_date: Date object or string in YYYY-MM-DD format
        """
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        self.do_poll(target_date)

    def do_poll(self, date):
        """Main polling logic that calls the API with the given date
        
        Args:
            date: Date object for the fromDate parameter
        """
        _logger.info(f'Starting booked appointment poll for date: {date}')
        
        # Check if poll already exists for this date
        poll = self.env['cz.booked_appointment_poll'].search([('date', '=', date)])
        if not poll:
            _logger.info('Creating a new booked appointment poll record...')
            poll = self.env['cz.booked_appointment_poll'].create([{
                'date': date,
            }])
        
        if poll.state == 'done':
            _logger.warning(f'Booked appointment poll already completed for date: {date}')
            return False

        # Get the API URL from system parameters (fallback to company settings)
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        url = IrConfigParameter.get_param('cz_pending_invoices.booked_appointment_url')
        
        # Fallback to company setting if system parameter not set
        if not url:
            url = self.env.company.booked_appointment_url
        
        if not url:
            _logger.error('No Booked Appointment API URL configured in system parameters or company settings')
            poll.state = 'error'
            return False

        # Build the complete URL with dynamic date
        # Format date as YYYY-MM-DD
        date_str = date.strftime('%Y-%m-%d')
        full_url = f'{url}?fromDate={date_str}'
        
        _logger.info(f'Calling Booked Appointment API: {full_url}')

        try:
            # Make the API request
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Add authorization if configured (check system parameter first, then company)
            token = IrConfigParameter.get_param('cz_pending_invoices.booked_appointment_token')
            if not token:
                token = self.env.company.booked_appointment_token
            
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            response = requests.get(full_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                _logger.error(f'Booked Appointment API returned status code: {response.status_code}')
                _logger.error(f'Response: {response.text}')
                poll.state = 'error'
                return False

            # Parse the JSON response
            appointments_data = response.json()
            _logger.info(f'Received {len(appointments_data) if isinstance(appointments_data, list) else 1} booked appointment(s)')

            # Process each appointment
            created_appointments = []
            for appointment_data in appointments_data if isinstance(appointments_data, list) else [appointments_data]:
                # Map the API response fields to model fields
                appointment_vals = {
                    'date': date,
                    'patient_name': appointment_data.get('patientName'),
                    'patient_id': appointment_data.get('patientId'),
                    'mrno': appointment_data.get('mrno'),
                    'mobile_no': appointment_data.get('mobileNo') or appointment_data.get('mobile'),
                    'appointment_id': appointment_data.get('appointmentId'),
                    'appointment_time': appointment_data.get('appointmentTime'),
                    'appointment_status': appointment_data.get('appointmentStatus') or appointment_data.get('status'),
                    'doctor_name': appointment_data.get('doctorName'),
                    'doctor_id': appointment_data.get('doctorId'),
                    'department': appointment_data.get('department', '').strip() if appointment_data.get('department') else '',
                    'service_name': appointment_data.get('serviceName'),
                    'speciality': appointment_data.get('speciality'),
                    'branch': appointment_data.get('branch', '').strip() if appointment_data.get('branch') else '',
                    'branch_code': appointment_data.get('branchCode', '').strip() if appointment_data.get('branchCode') else '',
                    'visit_type': appointment_data.get('visitType'),
                    'priority': appointment_data.get('priority'),
                    'reason': appointment_data.get('reason'),
                    'notes': appointment_data.get('notes'),
                    'confirmation_status': appointment_data.get('confirmationStatus'),
                }
                
                # Convert appointment date if present
                appointment_date = appointment_data.get('appointmentDate')
                if appointment_date:
                    try:
                        if isinstance(appointment_date, (int, float)):
                            appointment_vals['appointment_date'] = datetime.fromtimestamp(int(appointment_date) / 1000)
                        elif isinstance(appointment_date, str):
                            appointment_vals['appointment_date'] = datetime.strptime(appointment_date, '%Y-%m-%d')
                    except (ValueError, TypeError) as e:
                        _logger.warning(f'Could not convert appointmentDate: {e}')
                        appointment_vals['appointment_date'] = False
                
                # Convert booking date if present
                booking_date = appointment_data.get('bookingDate')
                if booking_date:
                    try:
                        if isinstance(booking_date, (int, float)):
                            appointment_vals['booking_date'] = datetime.fromtimestamp(int(booking_date) / 1000)
                        elif isinstance(booking_date, str):
                            appointment_vals['booking_date'] = datetime.strptime(booking_date, '%Y-%m-%d')
                    except (ValueError, TypeError) as e:
                        _logger.warning(f'Could not convert bookingDate: {e}')
                        appointment_vals['booking_date'] = False
                
                # Create the appointment record
                appointment = self.env['cz.booked_appointment'].create([appointment_vals])
                created_appointments.append(appointment)
                _logger.info(f'Created booked appointment record ID: {appointment.id} for patient {appointment.patient_name}')

            # Mark poll as done
            poll.state = 'done'
            _logger.info(f'Booked appointment poll completed successfully for date: {date}. Created {len(created_appointments)} records.')
            return created_appointments

        except requests.exceptions.RequestException as e:
            _logger.error(f'Booked Appointment API request failed: {str(e)}')
            poll.state = 'error'
            return False
        except Exception as e:
            _logger.error(f'Unexpected error during booked appointment poll: {str(e)}', exc_info=True)
            poll.state = 'error'
            return False

