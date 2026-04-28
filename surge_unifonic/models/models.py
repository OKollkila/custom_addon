# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Company(models.Model):
     _inherit = 'res.company'

     unifonic_public_id = fields.Char(string='Unifonic Public ID')
     unifonic_secret = fields.Char(string='Unifonic Secret')

