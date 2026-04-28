import base64
import logging
from datetime import datetime, timedelta

import requests
from odoo import models, fields


_logger = logging.getLogger(__name__)

class CheckoutPoll(models.Model):
    _name = 'cz.prime_care_checkout_poll'
    _description = 'cz.prime_care_checkout_poll'
    _sql_constraints = [('unique_date', 'UNIQUE(date)', 'Date must be unique')]

    date = fields.Date(string='Date')
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='new')

    def create_prime_care_token(self):
        _logger.info('create_prime_care_token')
        if not self.env.company.prime_care_login_url:
            _logger.warning('No Prime Care Login URL')
            return
        if not self.env.company.prime_care_username:
            _logger.warning('No Prime Care Username')
            return
        if not self.env.company.prime_care_password:
            _logger.warning('No Prime Care Password')
            return

        response = requests.post(self.env.company.prime_care_login_url, headers={'Content-Type': 'application/json'}, json={
            'username': self.env.company.prime_care_username,
            'password': base64.b64encode(self.env.company.prime_care_password.encode('utf-8')),
        })
        if response.status_code != 200:
            _logger.error('Token not created')

        json = response.json()
        self.env.company.prime_care_token = json.get('token')
        self.env.company.prime_care_company = json.get('companyCode')
        self.env.company.prime_care_division = json.get('divisionCode')
        _logger.info('Token created')

    def prime_care_poll_yesterday(self):
        yesterday = (datetime.today() - timedelta(days=1)).date()
        self.do_prime_care_poll(yesterday)

    def do_prime_care_poll(self, date):
        _logger.info('prime_care_poll')
        poll = self.env['cz.prime_care_checkout_poll'].search([('date', '=', date)])
        if not poll:
            _logger.info('Creating a new poll...')
            poll = self.env['cz.prime_care_checkout_poll'].create([{
                'date': date,
            }])
        if poll.state == 'done':
            _logger.warning('Poll already done')
            return False

        _logger.info('Sending Prime Care Poll...')
        if not self.env.company.prime_care_token:
            self.create_prime_care_token()
        # Get the URL from the config
        url = self.env.company.prime_care_checkouts_url
        if not url:
            _logger.warning('No URL')
            poll.state = 'error'
            return False

        url = f'{url}?date={date}'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.env.company.prime_care_token}',
            'Company': self.env.company.prime_care_company,
            'AllowedDivisions': self.env.company.prime_care_division,
            'Divisions': self.env.company.prime_care_division,
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            _logger.error('Error in the response')
            poll.state = 'error'
            return False

        json = response.json()
        ret = []
        for checkout in json:
            checkout[3] = checkout[3].strip()
            checkout[4] = checkout[4].strip()
            co = self.env['clinizone.checkout'].create([{
                'date': date,
                'mrno': checkout[0],
                'patient_name': checkout[1],
                'mobile_number': checkout[2],
                'department': checkout[3],
                'branch': checkout[4],
                'branch_ar': checkout[5],
                'doctor_name_en': checkout[6],
                'doctor_name': checkout[9],
                'machine_name': checkout[7],
                'technician_name': checkout[8],
                'payment_type_string': checkout[10],
            }])
            ret.append(co)

        poll.state = 'done'
        return ret
