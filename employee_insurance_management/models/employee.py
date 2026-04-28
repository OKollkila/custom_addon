# -*- coding: utf-8 -*-

from odoo import fields, models, api


class HREmployee(models.Model):
    _inherit = "hr.employee"

    @api.depends('insurance_ids')
    def _compute_is_create_insurance(self):
        for rec in self:
            if len(rec.insurance_ids) > 0:
                rec.is_create_insurance = True
            else:
                rec.is_create_insurance = False


    insurance_ids = fields.One2many(
        'employee.insurance', 
        'employee_id', 
        string='Insurance'
    )
    is_create_insurance = fields.Boolean(
        string='Is Create Insurance?',
        compute = '_compute_is_create_insurance',
        copy=False
    )


    # @api.multi
    def action_create_insurance(self):
        compose_form_id = self.env.ref("employee_insurance_management.view_employee_insurance_form_view").id
        ctx = {
            'default_name':self.name,
            'default_employee_id': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form_compute_is_create_insurance',
            'res_model': 'employee.insurance',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'current',
            'context': ctx,
        }

    # @api.multi
    def action_button_insurance(self):
        self.ensure_one()
        action = self.env.ref("employee_insurance_management.action_employee_insurance_view").read([])[0]
        action['domain'] = [('employee_id','=',self.id)]
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
