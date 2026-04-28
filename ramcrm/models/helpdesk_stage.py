from odoo import models, fields


class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _inherit = 'helpdesk.stage'

    is_close = fields.Boolean(default=False)
