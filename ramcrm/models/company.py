from odoo import models, fields


class Company(models.Model):
    _name = "res.company"
    _inherit = 'res.company'

    infinito_from = fields.Char(string="Infinito From")
    infinito_client_id = fields.Char(string="Infinito Client ID")
    infinito_client_password = fields.Char(string="Infinito Client Password")