# -*- coding: utf-8 -*-

from odoo import fields, models

class HelpdeskTicketType(models.Model):
    _inherit = 'helpdesk.ticket.type'

    disable_sms = fields.Boolean(
        string='Disable SMS Notifications',
        help='If checked, SMS notifications will not be sent for tickets of this type.'
    )
