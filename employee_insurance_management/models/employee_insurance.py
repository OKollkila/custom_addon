# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime, time
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class EmployeeInsurance(models.Model):
    _name = "employee.insurance"
    _description = 'Employee Insurance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Name",
        required=True
    )
    property_line_ids = fields.One2many(
        'employee.insurance.property.line', 
        'insurance_id', 
        string='Property Line'
    )
    phone = fields.Char(
        string="Phone",
        copy=True
    )
    email = fields.Char(
        string="Email",
        copy=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Insurance Holder",
        required=True,
        copy=True
    )
    contact_person = fields.Char(
        string="Contact Person",
    )
    policy_no = fields.Char(
        string="Insurance Number",
        copy=False
    )
    policy_company_id = fields.Many2one(
        'res.partner',
        string="Insurance Company",
        copy=True,
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id,
        required=True
    )
    policy_taken = fields.Date(
        string="Insurance Issued Date"
    )

    start_date = fields.Date(
        string='Insurance Start', 
        required=True,
        copy=False
    )
    end_date = fields.Date(
        string='Insurance End',
        required=True,
        copy=False
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True
    )
    internal_notes = fields.Text(
        string='Internal note'
    )
    amount = fields.Float(
        string='Insurance Amount',
        required=True
    )
    responsible_user_id = fields.Many2one(
        'res.users', 
        string='Responsible User',
        default=lambda s: s.env.uid,
        required=True
    )
    user_id = fields.Many2one(
        'res.users', string='Created by', 
        default=lambda s: s.env.uid,
        required=True,
        readonly=True
    )
    currency_id = fields.Many2one('res.currency',
        string='Currency', 
        readonly=True, 
        default=lambda self: self.env.user.company_id.currency_id
    )
    parent_id = fields.Many2one('employee.insurance',
        string="Previous Insurance",
        readonly=True,
        copy=False
    )
    state = fields.Selection(
        selection=[
            ('draft', 'New'), 
            ('confirm', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('to_expired', 'Expire Soon'),
            ('expired', 'Expired'),
            ('cancel', 'Cancelled'),
            ('close', 'Closed')
        ],
        default='draft',
        string='Status',
        tracking=True,
        copy=False
    )

    @api.model
    def _start_reminder(self):
        policy_days = self.env["ir.config_parameter"].sudo().get_param("employee_insurance_management.employee_insurance_expire_days")
        start_date=fields.Date.today() + relativedelta(days = int(policy_days))

        insurance_line = self.search([
            ('end_date','=',start_date),('state','=','in_progress')])
        for line in insurance_line:
            daily_missing_day = []
            daily_missing_day.append(start_date.strftime("%d-%m-%Y"))
            template = self.env.ref('employee_insurance_management.employee_insurance_management_reminder')
            template.send_mail(line.id)
            line.state='to_expired'

        insurance_line_to_expire = self.search([
            ('end_date','<=',start_date),('state','=','to_expired'), ('id','not in',insurance_line.ids)])
        insurance_line_to_expire.write({'state' :'expired'})

    # @api.multi
    def action_confirm(self):
        self.write({'state': 'confirm'})
        return True

    # @api.multi
    def action_progress(self):
        self.write({'state': 'in_progress'})
        return True
    
    # @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True
    
    # @api.multi
    def action_button_equipment(self):
        self.ensure_one()
        action = self.env.ref("hr.open_view_employee_list_my").read([])[0]
        action['domain'] = [('id','=',self.employee_id.id)]
        return action

    # @api.multi
    def unlink(self):
        for request in self:
            if request.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an Employee Insurance'))
        return super(MaintenanceEquipmentInsurance, self).unlink()


    @api.onchange('policy_company_id')
    def onchange_policy_compny(self):
        if self.policy_company_id:
            self.phone = self.policy_company_id.phone
            self.email = self.policy_company_id.email

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
