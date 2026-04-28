# -*- coding: utf-8 -*-

from odoo import fields, models ,api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    
    employee_insurance_expire_days = fields.Char(
        string="Employee Insurance Expiry Reminder Days"
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['employee_insurance_expire_days'] =self.env['ir.config_parameter'].sudo().get_param(
            'employee_insurance_management.employee_insurance_expire_days', default=0
        )
        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'employee_insurance_management.employee_insurance_expire_days', self.employee_insurance_expire_days
            )
        return super(ResConfigSettings, self).set_values()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
