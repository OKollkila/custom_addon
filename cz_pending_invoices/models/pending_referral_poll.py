import logging
from datetime import datetime, timedelta

import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)


class PendingReferralPoll(models.Model):
    _name = 'cz.pending_referral_poll'
    _description = 'Pending Referral Poll'
    _sql_constraints = [('unique_date', 'UNIQUE(date)', 'Date must be unique')]

    date = fields.Date(string='Date')
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='new')

    def poll_yesterday(self):
        """Poll for referrals from yesterday"""
        yesterday = (datetime.today() - timedelta(days=1)).date()
        self.do_poll(yesterday)

    def poll_today(self):
        """Poll for referrals from today"""
        today = datetime.today().date()
        self.do_poll(today)

    def poll_custom_date(self, target_date):
        """Poll for referrals from a specific date
        
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
        _logger.info(f'Starting referral poll for date: {date}')
        
        # Check if poll already exists for this date
        poll = self.env['cz.pending_referral_poll'].search([('date', '=', date)])
        if not poll:
            _logger.info('Creating a new referral poll record...')
            poll = self.env['cz.pending_referral_poll'].create([{
                'date': date,
            }])
        
        if poll.state == 'done':
            _logger.warning(f'Referral poll already completed for date: {date}')
            return False

        # Get the API URL from system parameters (fallback to company settings)
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        url = IrConfigParameter.get_param('cz_pending_invoices.pending_referral_url')
        
        # Fallback to company setting if system parameter not set
        if not url:
            url = self.env.company.pending_referral_url
        
        if not url:
            _logger.error('No Pending Referral API URL configured in system parameters or company settings')
            poll.state = 'error'
            return False

        # Build the complete URL with dynamic date
        # Format date as YYYY-MM-DD
        date_str = date.strftime('%Y-%m-%d')
        full_url = f'{url}?fromDate={date_str}'
        
        _logger.info(f'Calling Referral API: {full_url}')

        try:
            # Make the API request
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Add authorization if configured (check system parameter first, then company)
            token = IrConfigParameter.get_param('cz_pending_invoices.pending_referral_token')
            if not token:
                token = self.env.company.pending_referral_token
            
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            response = requests.get(full_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                _logger.error(f'Referral API returned status code: {response.status_code}')
                _logger.error(f'Response: {response.text}')
                poll.state = 'error'
                return False

            # Parse the JSON response
            referrals_data = response.json()
            _logger.info(f'Received {len(referrals_data) if isinstance(referrals_data, list) else 1} referral(s)')

            # Process each referral
            created_referrals = []
            for referral_data in referrals_data if isinstance(referrals_data, list) else [referrals_data]:
                # Map the API response fields to model fields
                referral_vals = {
                    'date': date,
                    'from_doctor': referral_data.get('fromDoctor'),
                    'to_doctor': referral_data.get('toDoctor'),
                    'visit_status': referral_data.get('visitStatus'),
                    'patient_name': referral_data.get('patientName'),
                    'mrno': referral_data.get('mrno'),
                    'service_name': referral_data.get('serviceName'),
                    'priority': referral_data.get('priority'),
                    'from_consultant_id': referral_data.get('fromConsultantId'),
                    'to_consultant_id': referral_data.get('toConsultantId'),
                    'action': referral_data.get('action'),
                    'branch': referral_data.get('branch', '').strip() if referral_data.get('branch') else '',
                    'department': referral_data.get('department', '').strip() if referral_data.get('department') else '',
                    'encounter_id': referral_data.get('encounterId', 0),
                    'speciality': referral_data.get('speciality'),
                    'patient_id': referral_data.get('patientId'),
                    'reason': referral_data.get('reason'),
                    'status': referral_data.get('status'),
                    'consultant_id': referral_data.get('consultantId'),
                    'branch_id_code': referral_data.get('branchId'),
                    'net_amt': referral_data.get('netAmt', 0.0),
                    'invoice_id': referral_data.get('invoiceId'),
                    'amount': referral_data.get('amount'),
                    'visit_no': referral_data.get('visitNo'),
                    'rejection_reason': referral_data.get('rejectionReason'),
                }
                
                # Convert timestamp fields (milliseconds to datetime)
                requested_date = referral_data.get('requestedDate')
                if requested_date:
                    try:
                        referral_vals['requested_date'] = datetime.fromtimestamp(int(requested_date) / 1000)
                    except (ValueError, TypeError) as e:
                        _logger.warning(f'Could not convert requestedDate: {e}')
                        referral_vals['requested_date'] = False
                
                visit_date = referral_data.get('visitDate')
                if visit_date:
                    try:
                        referral_vals['visit_date'] = datetime.fromtimestamp(int(visit_date) / 1000)
                    except (ValueError, TypeError) as e:
                        _logger.warning(f'Could not convert visitDate: {e}')
                        referral_vals['visit_date'] = False
                
                # Create the referral record
                referral = self.env['cz.pending_referral'].create([referral_vals])
                created_referrals.append(referral)
                _logger.info(f'Created referral record ID: {referral.id} for patient {referral.patient_name}')

            # Mark poll as done
            poll.state = 'done'
            _logger.info(f'Referral poll completed successfully for date: {date}. Created {len(created_referrals)} records.')
            return created_referrals

        except requests.exceptions.RequestException as e:
            _logger.error(f'Referral API request failed: {str(e)}')
            poll.state = 'error'
            return False
        except Exception as e:
            _logger.error(f'Unexpected error during referral poll: {str(e)}', exc_info=True)
            poll.state = 'error'
            return False

