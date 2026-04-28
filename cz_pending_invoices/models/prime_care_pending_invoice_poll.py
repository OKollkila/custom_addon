import base64
import logging
from datetime import datetime, timedelta

import requests
import yaml
from odoo import models, fields


_logger = logging.getLogger(__name__)

class PendingInvoicePoll(models.Model):
    _name = 'cz.prime_care_pending_invoice_poll'
    _description = 'cz.prime_care_pending_invoice_poll'
    _sql_constraints = [('unique_date', 'UNIQUE(date)', 'Date must be unique')]

    date = fields.Date(string='Date')
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='new')

    def create_prime_care_token(self):
        _logger.info('create_prime_care_token')
        if not self.env.company.prime_care_pending_invoice_login_url:
            _logger.warning('No Prime Care Missed Invoice Login URL')
            return
        if not self.env.company.prime_care_pending_invoice_username:
            _logger.warning('No Prime Care Missed Invoice Username')
            return
        if not self.env.company.prime_care_pending_invoice_password:
            _logger.warning('No Prime Care Missed Invoice Password')
            return

        response = requests.post(self.env.company.prime_care_pending_invoice_login_url, headers={'Content-Type': 'application/json'}, json={
            'username': self.env.company.prime_care_pending_invoice_username,
            'password': base64.b64encode(self.env.company.prime_care_pending_invoice_password.encode('utf-8')).decode(),
        })
        if response.status_code != 200:
            _logger.error('Token not created')

        json = response.json()
        self.env.company.prime_care_pending_invoice_token = json.get('token')
        self.env.company.prime_care_pending_invoice_company = json.get('companyCode')
        self.env.company.prime_care_pending_invoice_division = json.get('divisionCode')
        _logger.info('Token created')

    def prime_care_poll_yesterday(self):
        yesterday = (datetime.today() - timedelta(days=1)).date()
        self.do_prime_care_poll(yesterday)

    def do_prime_care_poll(self, date):
        _logger.info('prime_care_poll')
        poll = self.env['cz.prime_care_pending_invoice_poll'].search([('date', '=', date)])
        if not poll:
            _logger.info('Creating a new poll...')
            poll = self.env['cz.prime_care_pending_invoice_poll'].create([{
                'date': date,
            }])
        if poll.state == 'done':
            _logger.warning('Poll already done')
            return False

        _logger.info('Sending Prime Care Poll...')
        if not self.env.company.prime_care_pending_invoice_token:
            self.create_prime_care_token()
        # Get the URL from the config
        url = self.env.company.prime_care_pending_invoice_url
        if not url:
            _logger.warning('No URL')
            poll.state = 'error'
            return False

        url = f'{url}?fromDate={date}'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.env.company.prime_care_pending_invoice_token}',
            'Company': self.env.company.prime_care_pending_invoice_company,
            'AllowedDivisions': self.env.company.prime_care_pending_invoice_division,
            'Divisions': self.env.company.prime_care_pending_invoice_division,
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            _logger.error('Error in the response')
            poll.state = 'error'
            return False

        json = response.json()
        ret = []
        for pending_invoice in json:
            pending_invoice["branch"] = pending_invoice["branch"].strip()
            pending_invoice["department"] = pending_invoice["department"].strip()
            co = self.env['cz.pending_invoice'].create([{
                'date': date,
                'consultant_name':        pending_invoice["consultantName"]        ,
                'consultant_id':          pending_invoice["consultantId"]          ,
                'patient_name':           pending_invoice["patientName"]           ,
                'patient_id':             pending_invoice["patientId"]             ,
                'insurance_company':      pending_invoice["insuranceCompany"]      ,
                'insurance_tpa':          pending_invoice["insuranceTPA"]          ,
                'invoice_status':         pending_invoice["invoiceStatus"]         ,
                'approval_status':        pending_invoice["approvalStatus"]        ,
                'branch':                 pending_invoice["branch"]                ,
                'invoice_id':             pending_invoice["invoiceId"]             ,
                'mobile_no':              pending_invoice["mobileNo"]              ,
                'mrno':                   pending_invoice["mrno"]                  ,
                'nationality':            pending_invoice["nationality"]           ,
                'nationality_id':         pending_invoice["nationalityId"]         ,
                'department':             pending_invoice["department"]            ,
                'payment_mode':           pending_invoice["paymentMode"]           ,
                'payment_type':           pending_invoice["paymentType"]           ,
                'gross_amt':              pending_invoice["grossAmt"]              ,
                'discount_amt':           pending_invoice["discountAmt"]           ,
                'patient_share':          pending_invoice["patientShare"]          ,
                'patient_vat':            pending_invoice["patientVat"]            ,
                'patient_share_total':    pending_invoice["patientShareTotal"]     ,
                'company_share':          pending_invoice["companyShare"]          ,
                'company_vat':            pending_invoice["companyVat"]            ,
                'company_share_total':    pending_invoice["companyShareTotal"]     ,
                'sub_total':              pending_invoice["subTotal"]              ,
                'vat':                    pending_invoice["vat"]                   ,
                'total':                  pending_invoice["total"]                 ,
                'balance':                pending_invoice["balance"]               ,
                'total_paid_cash':        pending_invoice["totalPaidCash"]         ,
                'total_paid_wallet':      pending_invoice["totalPaidWallet"]       ,
                'total_paid_card':        pending_invoice["totalPaidCard"]         ,
                'total_paid_installment': pending_invoice["totalPaidInstallment"]  ,
                'total_paid_online':      pending_invoice["totalPaidonline"]       ,
                'invoice_date':           pending_invoice["invoiceDate"],
                'services_json':          pending_invoice["items"],
                'services':               yaml.dump(pending_invoice["items"], default_flow_style=False, allow_unicode=True),
            }])
            ret.append(co)

        poll.state = 'done'
        return ret
