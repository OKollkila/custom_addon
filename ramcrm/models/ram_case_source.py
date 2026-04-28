from odoo import models, fields

class RamCaseSource(models.Model):
    _name = 'clinizone.ram_case_source'
    _description = 'Case Source'

    name = fields.Char()
    created_by_customer = fields.Boolean()