from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Address field to track which location/partner the employee was at
    address_id = fields.Many2one(
        'res.partner',
        string='Address',
        help='The address/location where the employee clocked in/out',
        domain=[('is_company', '=', False)]  # Only show contacts, not companies
    )
    out_address_id = fields.Many2one(
        'res.partner',
        string='Address',
        help='The address/location where the employee clocked in/out',
        domain=[('is_company', '=', False)]  # Only show contacts, not companies
    )