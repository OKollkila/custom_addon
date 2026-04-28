# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class TopGoinfinitoTemplate(models.Model):
    """SMS template model for Goinfinito messages."""
    _name = 'top.goinfinito.template'
    _description = 'Goinfinito SMS Template'
    _order = 'template_type, name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help='Internal name for this template',
    )
    template_type = fields.Selection(
        [
            ('ticket_created', 'Ticket Created'),
            ('ticket_closed', 'Ticket Closed'),
        ],
        string='Template Type',
        required=True,
        help='When this template should be used',
    )
    body_ar = fields.Text(
        string='Arabic Body',
        required=True,
        help='SMS message body in Arabic. Use # to represent ticket name.',
    )
    body_en = fields.Text(
        string='English Body',
        required=True,
        help='SMS message body in English. Use # to represent ticket name.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company this template belongs to (leave empty for all companies)',
    )

    def render_template(self, ticket_name):
        """
        Render template with ticket name replacement.
        
        :param ticket_name: The ticket name/number to replace # with
        :return: Combined Arabic and English message
        """
        self.ensure_one()
        body_ar = (self.body_ar or '').replace('#', ticket_name)
        body_en = (self.body_en or '').replace('#', ticket_name)
        
        # Combine Arabic and English
        if body_ar and body_en:
            return f"{body_ar}\n{body_en}"
        elif body_ar:
            return body_ar
        elif body_en:
            return body_en
        return ''

    @api.model
    def get_template(self, template_type, company_id=None):
        """
        Get template by type and company.
        Priority order:
        1. Company-specific template (if company_id provided and not False)
        2. Current user's active company template (if company_id is None/False and user has company)
        3. Global template (company_id = False)
        """
        domain = [
            ('template_type', '=', template_type),
        ]
        
        # If company_id provided and not False, search for company-specific first
        if company_id:
            # First try company-specific template
            template = self.search(
                domain + [('company_id', '=', company_id)],
                limit=1,
                order='id desc'
            )
            if template:
                return template
        
        # If company_id is False (ticket has no company), try current user's company template
        if company_id is False and self.env.company:
            current_company_id = self.env.company.id
            template = self.search(
                domain + [('company_id', '=', current_company_id)],
                limit=1,
                order='id desc'
            )
            if template:
                return template
        
        # Fallback to global template (company_id = False)
        template = self.search(
            domain + [('company_id', '=', False)],
            limit=1,
            order='id desc'
        )
        return template if template else self.env['top.goinfinito.template']

