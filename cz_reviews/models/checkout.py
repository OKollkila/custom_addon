import logging
from datetime import datetime, timedelta

from odoo import models, fields, api

from ...surge_unifonic.unifonic import send_whatsapp

_logger = logging.getLogger(__name__)

class Checkout(models.Model):
    _name = 'clinizone.checkout'
    _description = 'clinizone.checkout'

    date = fields.Date(string='Date')
    mrno = fields.Char(string='MRN')
    patient_name = fields.Char(string='Patient Name')
    mobile_number = fields.Char(string='Mobile Number')
    department_id = fields.Many2one('clinizone.department', string='Department', compute='_compute_department_id', store=True)
    branch_id = fields.Many2one('clinizone.branch', string='Branch', compute='_compute_branch_id', store=True)
    branch = fields.Char(string='Branch Name')
    branch_ar = fields.Char(string='Branch Arabic')
    department = fields.Char(string='Department Name')
    doctor_name = fields.Char(string='Doctor Name')
    doctor_name_en = fields.Char(string='Doctor English Name')
    machine_name = fields.Char(string='Machine Name')
    technician_name = fields.Char(string='Technician Name')
    payment_type_string = fields.Char(string='Payment Type')
    review_message_sent_date_whatsapp = fields.Datetime(string='Review WhatsApp Message Sent Date', index=True)
    review_message_whatsapp_response = fields.Text(string='Review WhatsApp Response', index=True)
    user_input_id = fields.Many2one('survey.user_input', string='Survey User Input')

    # def old_create_user_input(self):
    #     _logger.info('old_create_user_input')
    #     self.ensure_one()
    #     if self.branch_id.company_id.checkout_survey_id and not self.user_input_id:
    #         _logger.info(f'Creating a user input for the survey: {self.branch_id.company_id.checkout_survey_id.title}...')
    #         self.user_input_id = self.env['survey.user_input'].sudo().create([{
    #             'survey_id': self.branch_id.company_id.checkout_survey_id.id,
    #             'checkout_id': self.id,
    #         }])
    #     else:
    #         _logger.info('No user input created')

    # def old_send_review_message_with_url_to_odoo_survey(self):
    #     _logger.info('old_send_review_message_with_url_to_odoo_survey')
    #     self.ensure_one()
    #     if self.branch_id.company_id.checkout_review_template and self.mobile_number and not self.review_message_sent_date_whatsapp and self.user_input_id:
    #         _logger.info('Sending review message for a created survey user input...')
    #         send_whatsapp(self.env, self.mobile_number, self.branch_id.company_id.checkout_review_template, ['url', self.user_input_id.absolute_url])
    #         self.sudo().review_message_sent_date_whatsapp = fields.Datetime.now()
    #     else:
    #         _logger.info('No review message sent')

    @api.depends('branch')
    def _compute_branch_id(self):
        for r in self:
            r.branch_id = self.env['clinizone.branch'].search([('prime_care_code', '=', r.branch)], limit=1).id,

    @api.depends('department')
    def _compute_department_id(self):
        for r in self:
            r.department_id = self.env['clinizone.department'].search([('prime_care_code', '=', r.department)], limit=1).id

    def send_unifonic_whatsapp_message(self):
        _logger.info('send_unifonic_whatsapp_message')
        self.ensure_one()
        if not self.mobile_number:
            self.review_message_whatsapp_response = 'No mobile number'
            _logger.warning('No mobile number')
            return False
        if self.review_message_sent_date_whatsapp:
            self.review_message_whatsapp_response = 'A WhatsApp message has already been sent'
            _logger.warning('A WhatsApp message has already been sent')
            return False

        template = self.branch_id.company_id.checkout_review_template
        if not template:
            self.review_message_whatsapp_response = f'No review template for the company: {self.branch_id.company_id.name}'
            _logger.warning(f'No review template for the company: {self.branch_id.company_id.name}')
            return False

        _logger.info(f'Sending WhatsApp message to {self.mobile_number} through Unifonic...')
        params = [
                    {
                        "type": "text",
                        "text": self.doctor_name
                    },
                    {
                        "type": "text",
                        "text": self.branch_ar,
                    }
                ]
        options_params = [
                    {
                        "value": f"{self.branch_ar}+{self.id}",
                        "subType": "quickReply",
                        "index": 0
                    }
                ]
        response = send_whatsapp(self.branch_id.company_id, self.mobile_number, template, params, options_params)
        self.sudo().review_message_sent_date_whatsapp = fields.Datetime.now()
        self.review_message_whatsapp_response = response
        self.env.cr.commit()
        return response

    def do_send_messages_for_yesterday(self):
        yesterday = (datetime.today() - timedelta(days=1)).date()
        self.do_send_messages(yesterday)

    def do_send_messages(self, date):
        _logger.info('do_send_messages')
        not_sent = self.env['clinizone.checkout'].search([('review_message_sent_date_whatsapp', '=', False), ('date', '=', date)], order='create_date')
        for checkout in not_sent:
            checkout.send_unifonic_whatsapp_message()
