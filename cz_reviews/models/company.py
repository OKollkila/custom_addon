from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    checkout_survey_id = fields.Many2one('survey.survey', string='Checkout Survey')
    checkout_review_template = fields.Char(string='Checkout Survey Unifonic Template')
