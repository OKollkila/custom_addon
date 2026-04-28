from odoo import models, fields, api

class MailActivity(models.Model):
    _name = 'mail.activity'
    _inherit = ['mail.activity', 'mail.thread']

    activity_type_id = fields.Many2one(tracking=True)
    date_deadline = fields.Date(tracking=True)
    summary = fields.Char(tracking=True)
    user_id = fields.Many2one(tracking=True)
    note = fields.Text(tracking=True)
    call_result = fields.Selection([
        ('booked', 'Booked'),
        ('no_answer', 'No Answer'),
        ('call_again', 'Call Again'),
        ('inquiry', 'Inquiry'),
        ('out_of_service', 'Out of Service'),
        ('switched_off', 'Switched Off'),
        ('busy', 'Busy'),
        ('hang_up_the_phone', 'Hang Up the Phone'),
        ('complaint', 'Complaint'),
        ('transferred_to_another_branch', 'Transferred to Another Branch'),
        ('will_call_back', 'Will Call Back'),
        ('price_issue', 'Price Issue'),
        ('already_booked', 'Already Booked'),
        ('not_interested', 'Not Interested'),
        ('wrong_number', 'Wrong Number'),
        ('duplicated', 'Duplicated'),
        ('visited', 'Visited'),
        ('rescheduled', 'Rescheduled'),
        ('satisfied', 'Satisfied'),
        ('waiting_list', 'Waiting List'),
    ], tracking=True)