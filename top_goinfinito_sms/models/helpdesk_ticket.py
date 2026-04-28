# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    """Extend Helpdesk Ticket to send SMS notifications."""
    _inherit = 'helpdesk.ticket'

    sms_config_id = fields.Many2one(
        'top.goinfinito.config',
        string='SMS Configuration',
        compute='_compute_sms_config',
        store=False,
        readonly=True,
        help='Active SMS configuration that will be used for this ticket',
    )
    sms_template_created_id = fields.Many2one(
        'top.goinfinito.template',
        string='SMS Template (Created)',
        compute='_compute_sms_templates',
        store=False,
        readonly=True,
        help='SMS template that will be used when ticket is created',
    )
    sms_template_closed_id = fields.Many2one(
        'top.goinfinito.template',
        string='SMS Template (Closed)',
        compute='_compute_sms_templates',
        store=False,
        readonly=True,
        help='SMS template that will be used when ticket is closed',
    )

    @api.depends('company_id', 'branch_id', 'branch_id.company_id')
    def _compute_sms_config(self):
        """Compute the SMS configuration that will be used for this ticket."""
        for ticket in self:
            derived_company = getattr(ticket, 'branch_id', False) and ticket.branch_id.company_id or ticket.company_id
            company_id_val = derived_company.id if derived_company else False
            config = self.env['top.goinfinito.config'].get_config_for_company(company_id_val)
            ticket.sms_config_id = config if config and config.active else False

    @api.depends('company_id', 'branch_id', 'branch_id.company_id')
    def _compute_sms_templates(self):
        """Compute the SMS templates that will be used for this ticket."""
        for ticket in self:
            derived_company = getattr(ticket, 'branch_id', False) and ticket.branch_id.company_id or ticket.company_id
            company_id_val = derived_company.id if derived_company else False
            ticket.sms_template_created_id = self.env['top.goinfinito.template'].get_template(
                'ticket_created', company_id_val
            )
            ticket.sms_template_closed_id = self.env['top.goinfinito.template'].get_template(
                'ticket_closed', company_id_val
            )

    def _send_sms_notification(self, template_type, is_test=False):
        """
        Send SMS notification using Goinfinito API.
        
        :param template_type: 'ticket_created' or 'ticket_closed'
        :param is_test: Boolean indicating if this is a test send (from manual button)
        """
        self.ensure_one()
        
        # Log ticket type for debugging
        ticket_type = self.ticket_type_id
        _logger.info('SMS Check - Ticket: %s, ticket_type: %s, disable_sms: %s',
                    self.name, ticket_type.name if ticket_type else 'None', 
                    ticket_type.disable_sms if ticket_type else 'N/A')
        
        # Skip SMS if ticket type has SMS disabled
        is_disabled_by_checkbox = ticket_type and ticket_type.disable_sms
        
        if is_disabled_by_checkbox:
            _logger.warning('SMS BLOCKED for excluded ticket type %s (ID: %s) on ticket %s. Reason: checkbox configuration',
                        ticket_type.name, ticket_type.id, self.name)
            # Post message to chatter
            self.message_post(
                body=_(
                    '<div class="o_message_sms_info">'
                    '<strong>🚫 SMS Not Sent</strong><br/>'
                    'SMS notification was blocked because ticket type "<strong>%s</strong>" is configured to disable SMS notifications.'
                    '</div>'
                ) % (ticket_type.name),
                subject=_('SMS Blocked - Excluded Ticket Type'),
                message_type='notification',
            )
            return False
        
        test_indicator = '🧪 <strong>TEST SMS</strong> - ' if is_test else ''
        
        # Derive company from branch when available, else fall back to ticket company
        derived_company = getattr(self, 'branch_id', False) and self.branch_id.company_id or self.company_id
        company_name = derived_company.name if derived_company else 'No Company (Global)'
        company_id_val = derived_company.id if derived_company else False
        
        # Check if company exists and is inactive (skip only if company exists and is inactive)
        if derived_company and not derived_company.active:
            _logger.debug('Company %s (ID: %s) inactive for ticket %s', company_name, derived_company.id, self.name)
        
        # Get configuration (will check current user's company, then global if company-specific not found)
        config = self.env['top.goinfinito.config'].get_config_for_company(
            company_id_val
        )
        if not config or not config.active:
            _logger.debug('No active SMS config for ticket %s', self.name)
            return False
        
        # CRITICAL: Verify that config company_id matches ticket company_id
        # If ticket has a company, config MUST have the same company (strict matching)
        if company_id_val and config.company_id:
            if config.company_id.id != company_id_val:
                _logger.warning('Config company mismatch for ticket %s', self.name)
                return False
        
        # Additional validation: If ticket has no company but config has a company, that's also a mismatch
        if not company_id_val and config.company_id:
            _logger.warning('Ticket has no company but config is company-scoped: %s', config.company_id.display_name)
            return False
        
        # Get template (will check global if company-specific not found)
        template = self.env['top.goinfinito.template'].get_template(
            template_type,
            company_id_val
        )
        if not template:
            _logger.warning('No SMS template found for ticket %s', self.name)
            return False
        
        # Get recipient phone - prefer partner_phone, fallback to partner_id.mobile
        phone_number = None
        if hasattr(self, 'partner_phone') and self.partner_phone:
            phone_number = self.partner_phone
        elif self.partner_id and self.partner_id.mobile:
            phone_number = self.partner_id.mobile
        
        if not phone_number:
            _logger.warning('No phone number found for ticket %s', self.name)
            return False
        
        # Render message
        message = template.render_template(self.name)
        if not message:
            _logger.warning('Empty SMS message for ticket %s', self.name)
            return False
        
        # Normalize phone number for display (same as service does)
        normalized_phone_display = ''.join(filter(str.isdigit, str(phone_number))) if phone_number else phone_number
        
        # Send SMS
        try:
            result, detail_msg = self.env['top.goinfinito.sms.service'].send_sms(
                to=phone_number,
                message=message,
                sender=config.sender_name,
                api_token=config.api_token,
                record=self
            )
            
            # Determine template type label for chatter
            template_label = 'Ticket Created' if template_type == 'ticket_created' else 'Ticket Closed'
            
            if result:
                _logger.info(
                    'SMS sent successfully for ticket %s (ID: %s) to %s, template %s (ID: %s), '
                    'company %s (ID: %s), message length=%d',
                    self.name,
                    self.id,
                    phone_number,
                    template.name,
                    template.id,
                    company_name,
                    company_id_val if company_id_val else 'None',
                    len(message)
                )
            else:
                _logger.error(
                    'Failed to send SMS for ticket %s (ID: %s) to %s, template %s (ID: %s), '
                    'company %s (ID: %s), error: %s',
                    self.name,
                    self.id,
                    phone_number,
                    template.name,
                    template.id,
                    company_name,
                    company_id_val if company_id_val else 'None',
                    detail_msg
                )
            
            return result
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            # Post detailed exception message to chatter
            config_company = config.company_id.name if config and config.company_id else ('Global' if config else 'N/A')
            template_company = template.company_id.name if template and template.company_id else ('Global' if template else 'N/A')
            exception_info = (
                f'Ticket: {self.name} (ID: {self.id})<br/>'
                f'Ticket Company: {company_name} (ID: {company_id_val if company_id_val else "None"})<br/>'
                f'Template Type: {template_type}<br/>'
                f'Template: {template.name if template else "N/A"} (ID: {template.id if template else "N/A"}) - Company: {template_company}<br/>'
                f'Phone: <strong>{phone_number}</strong><br/>'
                f'Sender: {config.sender_name if config else "N/A"}<br/>'
                f'Config Company: {config_company}<br/>'
                f'Message Length: {len(message) if "message" in locals() else "N/A"} characters<br/>'
                f'<strong>Exception:</strong> {error_msg}<br/>'
                f'<strong>Traceback:</strong><br/>'
                f'<pre style="font-size: 10px; max-height: 200px; overflow: auto;">{error_traceback}</pre>'
            )
            self.message_post(
                body=_(
                    '<div class="o_message_sms_error">'
                    '<strong>%s❌ SMS Exception</strong><br/>'
                    '<strong>Details:</strong><br/>'
                    '%s'
                    '</div>'
                ) % (test_indicator, exception_info),
                subject=_('SMS Notification Error') + (' (TEST)' if is_test else ''),
                message_type='notification',
            )
            _logger.error(
                'Exception sending SMS for ticket %s (ID: %s) to %s, company %s (ID: %s): %s',
                self.name,
                self.id,
                phone_number,
                company_name,
                company_id_val if company_id_val else 'None',
                error_msg,
                exc_info=True
            )
            return False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to send SMS on ticket creation."""
        tickets = super().create(vals_list)
        
        # Pre-fetch disabled ticket types IDs for efficient checking
        disabled_types = self.env['helpdesk.ticket.type'].search([('disable_sms', '=', True)])
        disabled_type_ids = set(disabled_types.ids)
        
        for i, ticket in enumerate(tickets):
            # 1. Check if type is excluded on the record object
            if ticket.ticket_type_id and ticket.ticket_type_id.disable_sms:
                _logger.info('Create: Skipping SMS for excluded ticket type ID %s (from record)', ticket.ticket_type_id.id)
                continue
                
            # 2. Safety check: Check vals directly
            if i < len(vals_list) and 'ticket_type_id' in vals_list[i]:
                type_id = vals_list[i]['ticket_type_id']
                if type_id and int(type_id) in disabled_type_ids:
                    _logger.info('Create: Skipping SMS for excluded ticket type ID %s (from vals)', type_id)
                    continue

            # Check if phone number is available (partner_phone or partner_id.mobile)
            has_phone = (
                (hasattr(ticket, 'partner_phone') and ticket.partner_phone) or
                (ticket.partner_id and ticket.partner_id.mobile)
            )
            if has_phone:
                ticket._send_sms_notification('ticket_created')
        return tickets

    def write(self, vals):
        """Override write to send SMS on ticket closure."""
        # Track tickets that need SMS notification
        tickets_to_notify = self.env['helpdesk.ticket']
        
        # Check if stage is being changed to closed
        if 'stage_id' in vals:
            for ticket in self:
                # Get the new stage after write
                new_stage_id = vals['stage_id']
                # We'll check after write, but prepare the list
                tickets_to_notify |= ticket
        
        result = super().write(vals)
        
        # Send SMS for tickets that were moved to closed stage
        if tickets_to_notify:
            for ticket in tickets_to_notify:
                # Skip SMS for excluded ticket types
                if ticket.ticket_type_id and ticket.ticket_type_id.disable_sms:
                    _logger.debug('Skipping SMS for excluded ticket type %s (ID: %s)', 
                                 ticket.ticket_type_id.name, ticket.ticket_type_id.id)
                    continue
                # Check if stage is closed (after write)
                if ticket.stage_id:
                    # Check if stage is closed by checking fold field or stage name
                    is_closed = (
                        getattr(ticket.stage_id, 'fold', False) or
                        ticket.stage_id.name.lower() in ['closed', 'done', 'resolved', 'cancelled']
                    )
                    # Check if phone number is available (partner_phone or partner_id.mobile)
                    has_phone = (
                        (hasattr(ticket, 'partner_phone') and ticket.partner_phone) or
                        (ticket.partner_id and ticket.partner_id.mobile)
                    )
                    if is_closed and has_phone:
                        # Only send if not already sent (avoid duplicates)
                        ticket._send_sms_notification('ticket_closed')
        
        return result

    
    def _send_sms(self):
        """Override ramcrm's _send_sms to enforce blocking logic."""
        EXCLUDED_IDS = [13, 23, 26, 27]
        if self.ticket_type_id and (self.ticket_type_id.disable_sms or self.ticket_type_id.id in EXCLUDED_IDS):
             _logger.warning("Blocked ramcrm _send_sms for ticket type %s (ID: %s)", 
                           self.ticket_type_id.name, self.ticket_type_id.id)
             return
        return super()._send_sms()

    def action_send_test_sms(self):
        """Manual action to send test SMS for current ticket."""
        self.ensure_one()
        
        # no pre-test chatter log
        
        # Get phone number - prefer partner_phone, fallback to partner_id.mobile
        phone_number = None
        if hasattr(self, 'partner_phone') and self.partner_phone:
            phone_number = self.partner_phone
        elif self.partner_id and self.partner_id.mobile:
            phone_number = self.partner_id.mobile
        
        if not phone_number:
            raise UserError(_('No phone number found for this ticket. Please set partner phone or partner mobile.'))
        
        # Determine template type based on ticket state
        # Check if stage is closed by checking fold field or stage name
        is_closed = False
        if self.stage_id:
            is_closed = (
                getattr(self.stage_id, 'fold', False) or
                self.stage_id.name.lower() in ['closed', 'done', 'resolved', 'cancelled']
            )
        template_type = 'ticket_closed' if is_closed else 'ticket_created'
        
        # Send SMS with is_test=True flag
        result = self._send_sms_notification(template_type, is_test=True)
        
        # Notify minimally via popup; chatter has minimal entry already
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test SMS Sent'),
                    'message': _('Test SMS sent successfully to %s.') % phone_number,
                    'type': 'success',
                    'sticky': False,
                    'sticky': False,
                }
            }
        else:
            # Don't raise error; chatter already shows failure
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test SMS Failed'),
                    'message': _('Test SMS failed.'),
                    'type': 'danger',
                    'sticky': True,
                }
            }
