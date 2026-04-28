# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    """Extend res.company to add assigned employees field."""
    
    _inherit = 'res.company'

    assigned_employee_ids = fields.Many2many(
        'hr.employee',
        'company_assigned_employee_rel',
        'company_id',
        'employee_id',
        string='Assigned Employees',
        help='Employees assigned to this company for specific operations or responsibilities. Can select employees from any company.'
    )
    
    assigned_employees_count = fields.Integer(
        string='Total Assigned Employees',
        compute='_compute_assigned_employees_count',
        store=False,
        help='Total number of employees assigned to this company.'
    )
    
    @api.model
    def _get_default_assigned_employees(self):
        """Get default assigned employees for the company."""
        return [(6, 0, [])]
    
    @api.depends('assigned_employee_ids')
    def _compute_assigned_employees_count(self):
        """Compute the total number of assigned employees."""
        for company in self:
            company.assigned_employees_count = len(company.assigned_employee_ids)
    
