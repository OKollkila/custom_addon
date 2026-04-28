from odoo import models, fields


class Status(models.Model):
    _name = 'cz.lead.status'
    _description = 'Lead Status'

    name = fields.Char("Name", required=True)