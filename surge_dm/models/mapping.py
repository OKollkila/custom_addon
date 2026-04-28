from odoo import fields, models

class Mapping (models.Model):
    _name = 'dm.mapping'
    _description = 'Mapping'

    old_name = fields.Char()
    new_name = fields.Char()
