# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class TopGoinfinitoConfig(models.Model):
    """Configuration model for Goinfinito SMS API settings."""
    _name = 'top.goinfinito.config'
    _description = 'Goinfinito SMS Configuration'
    _order = 'company_id, id'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        default=lambda self: _('Goinfinito SMS Configuration'),
    )
    api_token = fields.Char(
        string='API Token',
        required=True,
        help='Goinfinito API token for authentication (Basic Auth)',
    )
    sender_name = fields.Char(
        string='Sender Name',
        required=True,
        help='Default sender name for SMS messages (e.g., SDCdental)',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=False,
        default=lambda self: self.env.company if self.env.company else False,
        help='Leave empty for global configuration (applies to all companies)',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to disable SMS sending for this company',
    )

    # Note: SQL constraint with WHERE clause may not work in all PostgreSQL versions
    # The Python constraint below handles this more reliably

    @api.constrains('active', 'company_id')
    def _check_active_config(self):
        """Ensure only one active config per company (or one global active config)."""
        for record in self:
            if record.active:
                company_id = record.company_id.id if record.company_id else False
                other_active = self.search([
                    ('company_id', '=', company_id),
                    ('active', '=', True),
                    ('id', '!=', record.id),
                ])
                if other_active:
                    config_type = 'global' if not record.company_id else f'company {record.company_id.name}'
                    raise ValidationError(_(
                        'Only one active %s configuration is allowed. '
                        'Please deactivate the existing configuration first.'
                    ) % config_type)

    @api.model
    def get_config_for_company(self, company_id=None):
        """
        Get active configuration for a company.
        Priority order:
        1. Company-specific config (if company_id provided and not False) - EXACT MATCH
        2. Current user's active company config (if company_id is None/False and user has company)
        3. Global config (company_id = False)
        
        IMPORTANT: If company_id is provided (not None and not False), it will ONLY return
        a config that matches that exact company_id. No fallback to other companies.
        """
        # If company_id is None, use current user's company
        if company_id is None:
            company_id = self.env.company.id if self.env.company else False
        
        # If company_id is provided (not False), STRICTLY match that company only
        if company_id:
            config = self.search([
                ('company_id', '=', company_id),
                ('active', '=', True),
            ], limit=1, order='id desc')
            if config:
                return config
            # If company_id was explicitly provided and no match found, return empty
            # (don't fallback to other companies - strict matching)
            return self.env['top.goinfinito.config']
        
        # If company_id is False (ticket has no company), try current user's company config
        if company_id is False and self.env.company:
            current_company_id = self.env.company.id
            config = self.search([
                ('company_id', '=', current_company_id),
                ('active', '=', True),
            ], limit=1, order='id desc')
            if config:
                return config
        
        # If no company-specific config found, try global config (company_id = False)
        global_config = self.search([
            ('company_id', '=', False),
            ('active', '=', True),
        ], limit=1, order='id desc')
        if global_config:
            return global_config
        
        # Return empty recordset if nothing found
        return self.env['top.goinfinito.config']

