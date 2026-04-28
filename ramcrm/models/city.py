from odoo import models, fields


class City(models.Model):
    _name = 'clinizone.city'
    _description = 'clinizone.city'

    code = fields.Char("External Code", required=True)
    name = fields.Char("Name", required=True)