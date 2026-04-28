# -*- coding: utf-8 -*-

import time
from datetime import datetime

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
# from odoo.exceptions import except_orm, Warning, RedirectWarning,ValidationError
from odoo.exceptions import RedirectWarning,ValidationError

# Datetime_FORMAT = '%Y-%m-%d'

class hr_shift(models.Model):
    _name = 'hr.approve.shift'
    _description = 'Employee Shift'
    _rec_name = 'employee_id'
    _order = 'name desc'


    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    name = fields.Char(
        string='Number',
        readonly=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'New'), 
            ('confirm', 'Confirmed'),
            ('approve', 'Approved'), 
            ('reject', 'Rejected'),
            ('cancel', 'Cancelled')
        ],
        string='Status', 
        readonly=True, 
        default='draft',
        # track_visibility='onchange'
        tracking=True,
    )
    date_from = fields.Datetime(
        string='Start Date', 
        required=True, 
        default=fields.datetime.now()
    ) 
    date_to = fields.Datetime(
        string='End Date', 
        readonly=True
    )
    employee_id = fields.Many2one(
        'hr.employee', 
        string="Employee",
        required=True,
    )
    shift_responsible_user_id = fields.Many2one(
        'res.users', 
        string='Shift Responsible',
        required=True
    )
    notes = fields.Text(
        string='Notes'
    )
    department_id = fields.Many2one(
        'hr.department', 
        string='Department'
    )
    manager_id = fields.Many2one(
        'hr.employee',
        'Employee Manager', 
        readonly=True, 
        copy=False
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True,
        default=lambda self: self.env.user.company_id
    )    
    sequence = fields.Char(
        string='Sequence', 
        readonly=True  
    )
    type_shift_id = fields.Many2one(
        'shift.type',
        string='Shift Type',
        required=True,
        # readonly=True,
    )
    description = fields.Text(
        'Description',
        readonly=True
    )
    internal_notes = fields.Text(
        'Internal Notes',
        readonly=True
    )
  
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        print("onchange_employee_idertcyubhijnok",self)
        if self.employee_id:
            self.company_id = self.employee_id.company_id.id
            self.department_id = self.employee_id.department_id 
            self.manager_id = self.employee_id.parent_id 

    # @api.multi
    def unlink(self):
        for request in self:
            if request.state not in ('draft', 'cancel'):
                raise ValidationError(_('You cannot delete an shift request which is not Confirmed and approved '))
        return super(hr_shift, self).unlink()
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.approve.shift')
        return super(hr_shift, self).create(vals)

    # @api.multi
    def set_to_draft(self):
        self.write({
            'state': 'draft',
        })
        return True
    
    # @api.multi
    def action_refuse(self):
        self.write({'state': 'reject'})
        return True
    
    
    # @api.multi
    def action_confirm(self):
        for record in self:
            record._check_date()
            record.write({'state':'confirm'})
        return True

    # @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    # @api.multi
    def hr_approval(self):
        for record in self:
            record._check_date() 
            record.write({'state':'approve'})
        return True


    @api.model   
    def _check_date(self):
        domain = [
            ('date_from', '<=', self.date_to),
            ('date_to', '>', self.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('id', '!=', self.id),
            ('state', 'not in', ['draft','cancel','reject']),
        ]
        nholidays = self.search_count(domain)
        if nholidays:
            raise ValidationError(_('You can not have 2 leaves that overlaps on the same day.'))


class hr_shift_type(models.Model):
    _name = 'shift.type'
    _description = 'Employee Shift Type'


    name = fields.Char(
        string='Name',
        required=True
    )
    time_start = fields.Float(
        string='Start Time',
        required=True
    )    
    time_end = fields.Float(
        string='End Time',
        required=True
    )
    internal_notes = fields.Text(
        'Internal Notes'
    )
                       