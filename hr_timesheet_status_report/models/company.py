# -*- coding: utf-8 -*-

# from openerp import fields, models
from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    color = fields.Integer(string='Color Index')
    pending_follower_ids = fields.Many2many(
        'hr.employee',
        string='Timesheet Status Followers',
        copy=True,
    )
