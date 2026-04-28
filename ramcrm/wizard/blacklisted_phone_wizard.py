from odoo import models, fields
from odoo.exceptions import ValidationError


class BlacklistedPhoneWizard(models.TransientModel):
    _name = 'ramcrm.blacklisted_phone_wizard'
    _description = "Blacklisted Phone Wizard"

    blacklisted_reason = fields.Char('Reason')

    def action_do(self):
        for record in self:
            selected_id = self.env.context.get('active_id')
            selected_record = self.env['crm.lead'].browse(selected_id)
            if record.blacklisted_reason:
                self.env['clinizone.blacklist'].create({
                    'phone': selected_record.phone,
                    'blacklist_reason': record.blacklisted_reason,
                })
            else:
                raise ValidationError('Please enter a reason for blacklisting the phone number')

            selected_record.is_phone_blacklisted = True
            return {'type': 'ir.actions.act_window_close'}
