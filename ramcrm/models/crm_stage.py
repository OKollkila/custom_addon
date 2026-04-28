from odoo import models, fields


class Stage(models.Model):
    _name = "crm.stage"
    _inherit = 'crm.stage'

    stage2 = fields.Selection([('untouched', 'Untouched'), ('touched', 'Touched'), ('booked', 'Booked'), ('lost', 'Lost')])
    stage3 = fields.Selection([('untouched', 'Untouched'), ('reached', 'Reached'), ('unreached', 'Unreached'), ('booked', 'Booked')])