from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    prime_care_login_url = fields.Char(string='Prime Care Login URL')
    prime_care_checkouts_url = fields.Char(string='Prime Care Checkouts URL')
    prime_care_company = fields.Char(string='Prime Care Company')
    prime_care_division = fields.Char(string='Prime Care Division')
    prime_care_username = fields.Char(string='Prime Care Username')
    prime_care_password = fields.Char(string='Prime Care Password')
    prime_care_token = fields.Char(string='Prime Care Token')
