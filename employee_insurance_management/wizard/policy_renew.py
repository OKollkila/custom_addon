# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeInsuranceWizard(models.TransientModel):
    _name = "employee.insurance.wizard"
    _description = 'Employee Insurance Wizard'

    start_date = fields.Date(
        string='Renew Start', 
        default=fields.Date.today(), 
        required=True
    )
    end_date = fields.Date(
        string='Renew End',
        required=True
    )

    # @api.multi
    def action_create_renew(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        policy = self.env[active_model].browse(active_ids)
        
        policy_move = policy.copy(default={
             'start_date': self.start_date,
             'end_date': self.end_date,
             'parent_id':policy.id,
        })

        for line in policy.property_line_ids :
                line.copy(default={
                     'insurance_id': policy_move.id,
                })


        action = self.env.ref('employee_insurance_management.action_employee_insurance_view').sudo().read()[0]
        action['domain'] = [('id','=',policy_move.id)]
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: