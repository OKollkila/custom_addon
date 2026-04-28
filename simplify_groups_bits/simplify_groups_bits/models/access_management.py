from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class access_management(models.Model):
    _inherit = "access.management"

    apply_by_group = fields.Boolean('Apply By Group')
    access_group_ids = fields.Many2many('access.group', 'access_group_access_management_rel_bits',
                                        'access_management_id', 'access_group_id', string='Access Groups')

    @api.onchange('apply_by_group')
    def _onchange_apply_by_group(self):
        for record in self:
            record.access_group_ids = False

    @api.onchange('access_group_ids')
    def onchange_access_group_ids(self):
        for rec in self:
            rec.user_ids = rec.access_group_ids.mapped('user_ids')
