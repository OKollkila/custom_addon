# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime
from odoo import models, fields, api, _

class EmployeeTravelRequest(models.Model):
    _name = 'employee.travel.request'
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Employee Travel Request'
    _rec_name = 'number'
    _order = 'id desc'
            
    @api.depends('departure_date','return_date')
    def _compute_days(self):
        for rec in self:
            if rec.return_date and rec.departure_date:
                rec.days = datetime.strptime(str(rec.return_date), "%Y-%m-%d  %H:%M:%S") - datetime.strptime(str(rec.departure_date), "%Y-%m-%d  %H:%M:%S")
            else:
                rec.days = False
    
    @api.depends('travel_expense_line_ids', 'travel_expense_line_ids.total_amount')
    def _compute_total_amount_expense(self):
        for rec in self:
            rec.total_expenses_amount = False
            for expense_line in rec.travel_expense_line_ids:
                rec.total_expenses_amount += expense_line.total_amount
       
    @api.depends('advance_payment_line_ids', 'advance_payment_line_ids.total_amount')
    def _compute_total_advance_payment(self):
        for rec in self:
            rec.paid_amount = False
            for advance_payment in rec.advance_payment_line_ids:
                rec.paid_amount += advance_payment.total_amount
            
    @api.model
    def create(self,vals):
        number = self.env['ir.sequence'].next_by_code('travel.request')
        date = fields.datetime.today()
        vals.update({
            'number': number,
            'request_date' : date,
            })
        result = super(EmployeeTravelRequest, self).create(vals)
        return result 
    
    number = fields.Char(
        string='Number',
        index=True,
        readonly= True,
        required=True,
        copy=False,
        default=lambda self: _('New'),
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required = True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id,
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        store=True,
        string="Currency",
        default=lambda self: self.env.user.currency_id,
        readonly=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string="Department",
    )
    request_id = fields.Many2one(
        'res.users',
        string='Request By',
        copy=False,
    )
    request_date = fields.Date(
        'Request Date',
        readonly=True,
        copy=False,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        'Manager',
    )
    job_id = fields.Many2one(
        'hr.job',
        'Job Position',
    )
    travel_expense_line_ids = fields.One2many(
        'travel.expense.line',
        'travel_request_id',
        copy=False,
    )
    purpose_travel = fields.Char(
        'Travel Purpose',
        required = True,
    )
    project_id = fields.Many2one(
        'project.project',
        'Project',
        required=True,
    )
    expence_sheet_id = fields.Many2one(
        'hr.expense.sheet',
        'Created Expense Sheet',
        readonly=True,
        copy=False,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
    )
    from_city = fields.Char(
        required=True,
        string='From City',
    )
    from_state_id = fields.Many2one(
        "res.country.state",
        string='From State',
        required=True,
    )
    from_country_id = fields.Many2one(
        'res.country',
        string='From Country',
        required=True,
    )
    street = fields.Char(
        string='Street'
    )
    street2 = fields.Char(
        string='Street2'
    )
    zip = fields.Char(
        string='zip'
    )
    city = fields.Char(
        required=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string='State',
        required=True,
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
    )
    phone = fields.Char(
        'Contact Number',
    )
    email = fields.Char(
        'Email',
    )
    mode_of_travel = fields.Selection(
        selection=[('flight','Flight'),
                     ('train','Train'),
                     ('bus','Bus'),],
        string='Request Mode of Travel',
        required = True,
    )
    departure_date = fields.Datetime(
        'Request Departure Date',
        required = True,
    )
    return_date = fields.Datetime(
        'Request Return Date',
        required = True,
    )
    days = fields.Char(
        'Days',
        readonly=True,
        compute = _compute_days
    )
    approve_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approve_date = fields.Date(
        'Approved Date',
        readonly= True,
        copy=False,
    )
    confirm_id = fields.Many2one(
        'res.users',
        string="Confirm By",
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        'Confirm Date',
        readonly=True,
        copy=False,
    )
    total_expenses_amount = fields.Float(
        string='Total Expenses Amount',
        compute='_compute_total_amount_expense',
        #digits=dp.get_precision('Account'),
        digits='Account',
    )
    state = fields.Selection(
        selection=[
                    ('draft','Draft'),
                    ('confirm','Confirmed'),
                    ('approve','Approved'),
                    ('return','Returned'),
                    ('reject','Rejected'),
                    ('expenses_submitted','Expenses Submitted'),
                    ('cancel','Canceled'),
                  ],
        string='State Selection',
        track_visibility='onchange',
        default=lambda self: _('draft'),
    )
    available_departure_date = fields.Datetime(
        'Available Departure Date',
    )
    available_return_date = fields.Datetime(
        'Available Return Date',
    )
    departure_mode_of_travel = fields.Selection(
        selection=[('flight','Flight'),
                     ('train','Train'),
                     ('bus','Bus'),],
        string='Departure Mode of Travel',
    )
    return_mode_of_travel = fields.Selection(
        selection=[('flight','Flight'),
                     ('train','Train'),
                     ('bus','Bus'),],
        string='Return Mode of Travel'
    )
    visa_agent_id = fields.Many2one(
        'res.partner',
        'Visa Agent',
    )
    ticket_booking_agent_id = fields.Many2one(
        'res.partner',
        'Ticket Booking Agent',
    )
    bank_id = fields.Many2one(
        'res.bank',
        string='Bank Name',
    )
    cheque_no = fields.Char(
        string='Cheque Number',
    )
    advance_payment_line_ids = fields.One2many(
        'travel.advance.payment',
        'travel_request_id',
        copy=False,
    )
    paid_amount = fields.Float(
        string='Advance Paid Amount',
        compute='_compute_total_advance_payment',
        #digits=dp.get_precision('Account'),
        digits='Account',
    )
    note = fields.Text(
    )

    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id.id
            rec.job_id = rec.employee_id.job_id.id
            rec.manager_id = rec.employee_id.parent_id.id
            rec.request_id = rec.employee_id.user_id.id

    # @api.multi
    def set_draft(self):
        self.write({
            'state' : 'draft',
        })

    # @api.multi
    def set_confirm(self):
        self.write({
            'state' : 'confirm',
            'confirm_id' : self.env.user.id,
            'confirm_date' : fields.datetime.today(),
        })

    # @api.multi
    def set_approve(self):
        self.write({
            'state' : 'approve',
            'approve_date' : fields.datetime.today(),
            'approve_id' : self.env.user.id,
        })

    # @api.multi
    def set_reject(self):
        self.write({
            'state' : 'reject',
        })

    # @api.multi
    def set_cancel(self):
        self.write({
            'state' : 'cancel',
        })

    # @api.multi
    def set_returned(self):
        self.write({
            'state' : 'return',
        })
        
    # @api.multi
    def create_expenses(self):
        if not self.travel_expense_line_ids:
            raise UserError(_("Please fill in expenses on the request form in order to create an expense."))
        self.write({
            'state':'expenses_submitted',
        })
        expense_line_ids = self.travel_expense_line_ids
        expense_obj = self.env['hr.expense']
        expense_sheet_obj = self.env['hr.expense.sheet']
        expense_ids = []
        for rec in self.travel_expense_line_ids:
            expense_vals = {
                'name' : rec.product_id.name,
                'date' : rec.date,
                'product_id' : rec.product_id.id,
                # 'unit_amount' : rec.unit_price,
                'price_unit' : rec.unit_price,
                'quantity' : rec.quantity,
                'employee_id' : self.employee_id.id,
                'state' : 'draft',
                # 'analytic_account_id' : self.analytic_account_id.id,
            }
            expense_id = expense_obj.create(expense_vals)
            expense_ids.append(expense_id.id)
        vals = {
            'name' : self.project_id.name,
            'employee_id' : self.employee_id.id,
            'payment_mode' : 'own_account',
            'company_id' : self.company_id.id,
            'state' : 'submit',
            'expense_line_ids' : [(6, 0, expense_ids)],
        }
        expense_sheet_id = expense_sheet_obj.create(vals)
        if expense_sheet_id:
            self.expence_sheet_id = expense_sheet_id
        return expense_sheet_id
        
    # @api.multi
    def action_view_expense_sheet(self):
        expenses = self.mapped('expence_sheet_id')
        action = self.env.ref('hr_expense.action_hr_expense_sheet_my_all').sudo().read()[0]
        if len(expenses) > 1:
            action['domain'] = [('id', 'in', expenses.ids)]
        elif len(expenses) == 1:
            action['views'] = [(self.env.ref('hr_expense.view_hr_expense_sheet_form').id, 'form')]
            action['res_id'] = expenses.ids[0]
        else:
            action = {'type': 'ir.actions.act_window'}
        return action
