from odoo import models, fields


class BusinessCategory(models.Model):
    _name = 'clinizone.business_category'
    _description = 'clinizone.business_category'

    name = fields.Char("Name", required=True)