from odoo import models, fields, _
from odoo.exceptions import UserError


class LocalUser(models.Model):
    _name = 'local_users_admin.user'
    _description = 'local_users_admin.user'

    user_id = fields.Many2one('res.users', string='User', required=True)
    name = fields.Char(string='Name', related='user_id.name', readonly=False)
    email = fields.Char(string='Email', related='user_id.login', readonly=False)
    all_group_ids = fields.Many2many('res.groups', string='All Groups', compute='_compute_all_permissions')
    selected_group_ids = fields.Many2many('res.groups', string='Selected Groups', domain="[('id', 'in', all_group_ids)]")
    company_id = fields.Many2one(related='user_id.company_id')

    def _compute_all_permissions(self):
        for record in self:
            allowed_groups = self.env['local_users_admin.allowed_group'].search([]).mapped('group_id')
            record.all_group_ids = allowed_groups.ids

    def write(self, vals):
        if self.env.user.company_id != self.user_id.company_id:
            raise UserError('You cannot edit a user from another company')

        vals = {key: vals[key] for key in vals if key in ['selected_group_ids', 'name', 'email']}

        ok = super(LocalUser, self.sudo()).write(vals)
        if not ok:
            return ok

        for group in self.user_id.groups_id:
            if group in self.all_group_ids and group not in self.selected_group_ids:
                self.sudo().user_id.groups_id = [(3, group.id)]

        for group in self.selected_group_ids:
            if group in self.all_group_ids and group not in self.user_id.groups_id:
                self.sudo().user_id.groups_id = [(4, group.id)]

        return ok

    def action_reset_password(self):
        self.ensure_one()

        if not self.env.user.has_group('local_users_admin.group_local_users_admin'):
            return

        message_type = 'success'
        message = _("Reset password email has been sent to the user")
        try:
            self.user_id.sudo().action_reset_password()
        except Exception as e:
            message = _("Error: %s" % e)
            message_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': message_type,
            },
        }

    def action_sync_users(self):
        users = self.env['res.users'].search([])
        for user in users:
            if not self.env['local_users_admin.user'].search([('user_id', '=', user.id)]):
                self.env['local_users_admin.user'].create({
                    'user_id': user.id,
                })

        # for local_user in self.env['local_users_admin.user'].search([]):
        #     for group in local_user.user_id.groups_id:
        #         if group in local_user.all_group_ids and group not in local_user.selected_group_ids:
        #             local_user.selected_group_ids = [(4, group.id)]
        #
        #     for group in local_user.selected_group_ids:
        #         if group not in local_user.user_id.groups_id or group not in local_user.all_group_ids:
        #             local_user.selected_group_ids = [(3, group.id)]