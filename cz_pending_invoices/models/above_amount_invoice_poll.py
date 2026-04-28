import logging
from datetime import datetime, timedelta

import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)


class AboveAmountInvoicePoll(models.Model):
    _name = 'cz.above_amount_invoice_poll'
    _description = 'Above Amount Invoice Poll'
    _sql_constraints = [('unique_date', 'UNIQUE(date)', 'Date must be unique')]

    date = fields.Date(string='Date')
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='new')

    def poll_yesterday(self):
        """Poll for invoices from yesterday"""
        yesterday = (datetime.today() - timedelta(days=1)).date()
        self.do_poll(yesterday)

    def poll_today(self):
        """Poll for invoices from today"""
        today = datetime.today().date()
        self.do_poll(today)

    def poll_custom_date(self, target_date):
        """Poll for invoices from a specific date
        
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
        _logger.info(f'Starting poll for date: {date}')
        
        # Check if poll already exists for this date
        poll = self.env['cz.above_amount_invoice_poll'].search([('date', '=', date)])
        if not poll:
            _logger.info('Creating a new poll record...')
            poll = self.env['cz.above_amount_invoice_poll'].create([{
                'date': date,
            }])
        
        if poll.state == 'done':
            _logger.warning(f'Poll already completed for date: {date}')
            return False

        # Get the API URL from system parameters (fallback to company settings)
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        url = IrConfigParameter.get_param('cz_pending_invoices.above_amount_invoice_url')
        
        # Fallback to company setting if system parameter not set
        if not url:
            url = self.env.company.above_amount_invoice_url
        
        if not url:
            _logger.error('No API URL configured in system parameters or company settings')
            poll.state = 'error'
            return False

        # Build the complete URL with dynamic date
        # Format date as YYYY-MM-DD
        date_str = date.strftime('%Y-%m-%d')
        full_url = f'{url}?fromDate={date_str}'
        
        _logger.info(f'Calling API: {full_url}')

        try:
            # Make the API request
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Add authorization if configured (check system parameter first, then company)
            token = IrConfigParameter.get_param('cz_pending_invoices.above_amount_invoice_token')
            if not token:
                token = self.env.company.above_amount_invoice_token
            
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            response = requests.get(full_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                _logger.error(f'API returned status code: {response.status_code}')
                _logger.error(f'Response: {response.text}')
                poll.state = 'error'
                return False

            # Parse the JSON response
            invoices_data = response.json()
            _logger.info(f'Received {len(invoices_data) if isinstance(invoices_data, list) else 1} invoice(s)')

            # Process each invoice
            created_invoices = []
            for invoice_data in invoices_data if isinstance(invoices_data, list) else [invoices_data]:
                # Map the API response fields to your model fields
                # Adjust this mapping based on your actual API response structure
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
                
                # Create the invoice record
                invoice = self.env['cz.above_amount_invoice'].create([invoice_vals])
                created_invoices.append(invoice)
                _logger.info(f'Created invoice record ID: {invoice.id}')

            # Mark poll as done
            poll.state = 'done'
            _logger.info(f'Poll completed successfully for date: {date}')
            return created_invoices

        except requests.exceptions.RequestException as e:
            _logger.error(f'Request failed: {str(e)}')
            poll.state = 'error'
            return False
        except Exception as e:
            _logger.error(f'Unexpected error during poll: {str(e)}', exc_info=True)
            poll.state = 'error'
            return False

