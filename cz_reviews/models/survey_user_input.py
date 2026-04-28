from odoo import models, fields


class UserInput(models.Model):
    _inherit = 'survey.user_input'

    checkout_id = fields.Many2one('clinizone.checkout', string='Checkout')
    absolute_url = fields.Char(string='Absolute URL', compute='_compute_absolute_url')

    def _compute_absolute_url(self):
        for r in self:
            r.absolute_url = '%s%s' % (r.get_base_url(), r.get_start_url())

