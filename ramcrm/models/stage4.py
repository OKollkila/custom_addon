from odoo import models, fields


class Stage4(models.Model):
    _name = 'cz.lead.stage4'
    _description = 'Lead Stage 4'

    name = fields.Char("Name", required=True)