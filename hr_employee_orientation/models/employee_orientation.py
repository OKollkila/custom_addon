# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MainChecklistConfig(models.Model):
    _name = 'main.checklist.config'
    _description = 'Main Checklist Configuration'
    
    name = fields.Char(
        string='Name',
        required=True,
    )
    main_checklist_ids = fields.Many2many(
        'hr.orientation.checklist.config',
        string='Checklist Configuration',
    )
    active_id = fields.Boolean(
        string='Active',
        default=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True
    )

class HrOrientationChecklistConfig(models.Model):
    _name = 'hr.orientation.checklist.config'
    _description = 'Hr Orientation Checklist Config'
    
    name = fields.Char(
        string='Name',
        required=True
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        required=True,
    )

class HrOrientationChecklist(models.Model):
    _name = 'hr.orientation.checklist'
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin']      #   odoo11
    
    _order = 'id desc'
    _rec_name = 'name'
    _description = "Orientation Checklist"

    name = fields.Char(
        string='Name',
        required=True
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        required=True,
    )
    checklist_state = fields.Selection(
        selection=[('new', 'New'), \
        ('done', 'Completed'),\
        ('cancel', 'Cancelled')],
        string='Status',
        default='new',
        # track_visibility='onchange'
        tracking=True
    )
    checklist_date = fields.Date(
        string='Date',
    )
    expected_date = fields.Date(
        string='Expected Date',
    )
    orientation_id = fields.Many2one(
        'hr.orientation',
        string='Orientation',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.user.company_id,
        string='Company',
        readonly=True
    )
    note = fields.Text(
        string='Notes'
    )
    attachment_ids1 = fields.Binary(
        string='First Attachment'
    )
    attachment_ids2 = fields.Binary(
        string='Second Attachment'
    )
    attachment_ids3 = fields.Binary(
        string='Third Attachment'
    )
    employee_id = fields.Many2one(
        related='orientation_id.employee_id',
        string='Employee User',
        readonly=True,
        store=True,
    )

class HrOrientation(models.Model):
    _name = 'hr.orientation'
    _description = 'hr.orientation'
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin']      #   odoo11
    
    _order = 'id desc'
    _rec_name = 'name'
    _description = 'Employee Orientation'

    name = fields.Char(
        string='Number'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        string="Employee",
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Title',
        required=True
    )
    parent_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        required=True
    )
    orientation_date = fields.Date(
        string='Date',
        default=fields.Date.today(),
        readonly=True,
        copy=False,
        required=True
    )
    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        string='Responsible User',
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.user.company_id,
        string='Company',
        readonly=True,
        required=True,
    )
    checklist_ids = fields.One2many(
        'hr.orientation.checklist', 
        'orientation_id',
        copy=False
    )
    state = fields.Selection(
        selection=[
        ('draft', 'Draft'), \
        ('confirm', 'Confirmed'), \
        ('cancel', 'Cancelled'), \
        ('done', 'Completed')],
        string='Status',
        readonly=True, 
        default='draft',
        # track_visibility='onchange'
        tracking=True,
    )
    note = fields.Text(
        string='Notes'
    )
    main_configuration_id = fields.Many2one(
        'main.checklist.config',
        string='Orientation Checklist',
        required=True,
    )
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.orientation')
        return super(HrOrientation, self).create(vals)

    @api.onchange('employee_id')
    def get_department(self):
        for line in self:
            line.department_id = line.employee_id.department_id.id
            line.job_id = line.employee_id.job_id.id
            line.parent_id = line.employee_id.parent_id.id
    
    @api.onchange('main_configuration_id')
    def onchange_main_configuration(self):
        vals = []
        for line in self.main_configuration_id.main_checklist_ids:
            vals.append((0,0,{'name': line.name,
                              'responsible_user_id':line.responsible_user_id.id ,
                              'checklist_state': 'new',
                              'checklist_date': fields.Date.today()
                              }))
        self.checklist_ids = vals
    
    #@api.multi
    def get_confirm(self):
        template = self.env.ref('hr_employee_orientation.email_template_employee_orientation1')
        for check in self.checklist_ids:
            template.send_mail(check.id, force_send=True)
        self.state = 'confirm'

    #@api.one
    def get_done(self):
        self.state = 'done'
    
    #@api.one
    def get_cancel(self):
        self.state = 'cancel'
    
    #@api.one
    def get_reset_to_draft(self):
        self.state = 'draft'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
