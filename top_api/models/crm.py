# models/crm_lead.py
from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='Select an employee for this lead'
    )
