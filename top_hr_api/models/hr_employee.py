# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Allow Multi Attendance Location field
    allow_multi_attendance_location = fields.Boolean(
        string='Allow Multi Attendance Location',
        default=False,
        help='If enabled, employee can have multiple attendance locations from Partner Assignments'
    )
