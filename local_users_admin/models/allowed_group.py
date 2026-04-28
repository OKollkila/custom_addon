from odoo import models, fields


class AllowedGroup(models.Model):
    _name = 'local_users_admin.allowed_group'
    _description = 'local_users_admin.allowed_group'

    group_id = fields.Many2one('res.groups', string='Group', required=True)
