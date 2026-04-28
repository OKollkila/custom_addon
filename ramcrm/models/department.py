from odoo import models, fields


class Department(models.Model):
    _name = 'clinizone.department'
    _description = 'clinizone.department'

    name = fields.Char("Name", required=True)