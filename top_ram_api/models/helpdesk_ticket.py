from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import logging
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode
import json
from html import escape

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'
    ram_id=fields.Char(string="RAM ID")
    invid = fields.Char(string="inv")
    refund_reason=fields.Text(string="Reason")

    # Validation disabled temporarily
    # @api.constrains('ticket_type_id', 'refund_reason', 'workflow_level')
    # def _check_refund_reason_required(self):
    #     """
    #     Make refund_reason required when:
    #     - ticket_type_id is 28, OR
    #     - workflow_level > 0
    #     """
    #     for ticket in self:
    #         # Check if reason is required based on ticket_type_id or workflow_level
    #         requires_reason = False
    #         
    #         if ticket.ticket_type_id and ticket.ticket_type_id.id == 28:
    #             requires_reason = True
    #         
    #         if ticket.workflow_level and int(ticket.workflow_level) > 0:
    #             requires_reason = True
    #         
    #         if requires_reason:
    #             if not ticket.refund_reason or not ticket.refund_reason.strip():
    #                 raise UserError(_('Reason is required when Ticket Type is 28 or Workflow Level is greater than 0.'))

    workflow_level_id = fields.Many2one(
        'workflow.level',
        string='Workflow Level',
        required=False,  # DB nullable to avoid querying workflow.level during schema init
        ondelete='restrict',
        help='Workflow level for RAM Prime Care API integration (default set in create/post_init)'
    )
    workflow_level_since = fields.Datetime(
        string='Workflow level since',
        readonly=True,
        help='When the ticket entered the current workflow level (used for escalation time)'
    )
    refund_processor_id = fields.Many2one('res.users', string="Refund Processor", tracking=True)
    is_level_4_completed = fields.Boolean(string="Completed by Level 4", default=False, tracking=True)

    is_level_4 = fields.Boolean(compute='_compute_is_level_4', store=True)

    is_refund_sent = fields.Boolean(string="تم إرسال الأموال", default=False, tracking=True)

    @api.model
    def _cron_escalate_workflow_level(self):
        """
        Cron to escalate tickets according to workflow levels.
        - Skips tickets in 'Rejected' stage.
        - Checks escalation hours.
        - Handles actions: upgrade_only, email_only, upgrade_and_email.
        - Skips escalation during weekends (Friday after 8pm until Sunday 8am).
        """
        now = datetime.utcnow()
        levels_with_escalation = self.env['workflow.level'].search([('escalation_hours', '>', 0)])
        if not levels_with_escalation:
            return

        rejected_stages = self.env['helpdesk.stage'].search([('name', 'ilike', 'rejected')])
        rejected_stage_ids = rejected_stages.ids

        tickets = self.search([
            ('ram_id', '!=', False),
            ('ram_id', '!=', ''),
            ('workflow_level_id', 'in', levels_with_escalation.ids),
            ('workflow_level_since', '!=', False),
            ('stage_id', 'not in', rejected_stage_ids),
        ])

        for ticket in tickets:
            level = ticket.workflow_level_id
            if not level or level.escalation_hours <= 0:
                continue

            since = ticket.workflow_level_since
            if not since:
                continue

            since_dt = since if isinstance(since, datetime) else datetime.strptime(str(since)[:19], '%Y-%m-%d %H:%M:%S')
            if since_dt.tzinfo:
                since_dt = since_dt.replace(tzinfo=None)  # naive UTC

            # Skip escalation on Friday after 8pm, Saturday, and Sunday before 8am
            weekday = now.weekday()  # Monday=0 .. Sunday=6
            if (weekday == 4 and now.hour >= 20) or (weekday == 5) or (weekday == 6 and now.hour < 8):
                continue

            delta = now - since_dt
            if delta < timedelta(hours=level.escalation_hours):
                continue

            action = level.escalation_action or 'upgrade_only'
            next_level = None
            if action != 'email_only':
                next_level = self.env['workflow.level'].search([('sequence', '>', level.sequence)],
                                                               order='sequence', limit=1)
                if not next_level:
                    continue

            # Send email if needed
            if action in ('email_only', 'upgrade_and_email') and level.escalation_email_user_id:
                try:
                    ticket.sudo()._send_escalation_email(level)
                except Exception as e:
                    _logger.exception("Failed to send escalation email for ticket %s: %s", ticket.name, e)

            # Upgrade to next level if needed
            if action in ('upgrade_only', 'upgrade_and_email') and next_level:
                ticket.sudo().with_context(skip_workflow_level_downgrade_check=True).write({
                    'workflow_level_id': next_level.id,
                    'workflow_level_since': fields.Datetime.now(),
                })
                _logger.info(
                    "Escalated ticket %s from level %s to %s (no update for %s hours)",
                    ticket.name, level.code, next_level.code, level.escalation_hours
                )

    def action_confirm_refund_sent(self):
        for record in self:
            if record.is_level_4_completed:
                record.is_refund_sent = True
                record.message_post(body="تم تأكيد إرسال الأموال لهذه التذكرة.")

    @api.depends('workflow_level_id')
    def _compute_is_level_4(self):
        for ticket in self:
            if hasattr(ticket,
                       'workflow_level_id') and ticket.workflow_level_id and ticket.workflow_level_id.name == 'Level 4':
                ticket.is_level_4 = True
            else:
                ticket.is_level_4 = False

    def action_complete_level_4(self):
        """الدالة التي تُنفذ عند الضغط يدوياً على زر الإكمال"""
        refund_group = self.env.ref('top_ram_api.group_helpdesk_refund_processor')
        processor_user = refund_group.users[:1]
        for ticket in self:
            ticket.is_level_4_completed = True
            if processor_user:
                ticket.refund_processor_id = processor_user.id
                ticket.message_post(body="تم إكمال المستوى 4 وإسناد التذكرة لمسؤول الـ Refund.")

    @api.model
    def _update_old_refund_tickets(self):
        """دالة لتحديث التذاكر القديمة التي لم يتم إسنادها"""
        refund_group = self.env.ref('top_ram_api.group_helpdesk_refund_processor', raise_if_not_found=False)
        if not refund_group or not refund_group.users:
            return

        processor_user = refund_group.users[0]
        old_tickets = self.search([
            ('is_level_4', '=', True),
            ('is_level_4_completed', '=', True),
            ('refund_processor_id', '=', False)
        ])
        if old_tickets:
            old_tickets.write({'refund_processor_id': processor_user.id})

    @api.model
    def _default_workflow_level_id(self):
        """Default workflow level (first by sequence). Not used as field default to avoid DB init errors."""
        level = self.env['workflow.level'].search([], order='sequence', limit=1)
        return level.id if level else False

    def _check_workflow_level_downgrade(self, vals):
        """Block lowering workflow level unless user has group_helpdesk_workflow_allow_downgrade.
        Only enforced for tickets that have ram_id set (RAM / Prime Care tickets).
        """
        if self.env.context.get('skip_workflow_level_downgrade_check'):
            return
        if 'workflow_level_id' not in vals:
            return
        if self.env.user.has_group('top_ram_api.group_helpdesk_workflow_allow_downgrade'):
            return
        new_id = vals.get('workflow_level_id')
        for ticket in self:
            if not ticket.ram_id or not str(ticket.ram_id).strip():
                continue
            old_level = ticket.workflow_level_id
            if not old_level:
                continue
            if not new_id:
                raise UserError(_(
                    'You cannot remove the workflow level. Users with "Allow workflow level downgrade" may change levels.'
                ))
            new_level = self.env['workflow.level'].browse(new_id)
            if not new_level.exists():
                continue
            if new_level.sequence < old_level.sequence:
                raise UserError(_(
                    'You cannot downgrade the workflow level from %(old)s to %(new)s. '
                    'Only users with the access right "Allow workflow level downgrade" can do this.'
                ) % {'old': old_level.display_name, 'new': new_level.display_name})

    # Team ID to keep when auto-assigning from branch workflow (ramcrm clears user_id if user not in team)
    ASSIGNMENT_TEAM_ID = 445

    def _assign_user_from_branch_workflow(self):
        """
        If ticket has ram_id, branch_id and workflow_level_id, assign the ticket
        to the user linked to that workflow level on the branch (clinizone.branch.workflow.line).
        Forces team_id to ASSIGNMENT_TEAM_ID (445) so the assignment is kept.
        """
        if self.env.context.get('skip_assign_user_from_branch'):
            return
        for ticket in self:
            if not ticket.ram_id or not getattr(ticket, 'branch_id', None) or not ticket.workflow_level_id:
                continue
            branch = ticket.branch_id
            if not hasattr(branch, 'workflow_line_ids') or not branch.workflow_line_ids:
                continue
            line = branch.workflow_line_ids.filtered(
                lambda l: l.workflow_level_id == ticket.workflow_level_id
            )[:1]
            if not line or not line.user_id:
                continue
            if ticket.user_id == line.user_id and ticket.team_id and ticket.team_id.id == self.ASSIGNMENT_TEAM_ID:
                continue
            # Force assign user and keep team_id 445 (ramcrm clears user_id when user not in team_id.member_ids)
            write_vals = {'user_id': line.user_id.id, 'team_id': self.ASSIGNMENT_TEAM_ID}
            ticket.sudo().with_context(skip_assign_user_from_branch=True).write(write_vals)
            _logger.info(
                "Assigned ticket %s to user %s (branch %s, workflow level %s), team_id=%s",
                ticket.name, line.user_id.login, branch.name, ticket.workflow_level_id.code, self.ASSIGNMENT_TEAM_ID
            )

    def _send_escalation_email(self, level):
        """Send escalation notification email to the user set on the workflow level."""
        self.ensure_one()
        if not level.escalation_email_user_id or not level.escalation_email_user_id.partner_id.email:
            return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        ticket_url = '%s/web#model=helpdesk.ticket&id=%s&view_type=form' % (base_url, self.id)
        subject = _('Escalation: Ticket %s at level %s for %s hours') % (
            self.name, level.name, level.escalation_hours
        )
        body_html = _(
            '<p>Ticket <strong>%s</strong> has been at workflow level <strong>%s</strong> for more than %s hours.</p>'
            '<p><a href="%s">Open ticket</a></p>'
        ) % (self.name, level.name, level.escalation_hours, ticket_url)
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_to': level.escalation_email_user_id.partner_id.email,
            'model': self._name,
            'res_id': self.id,
        })
        try:
            mail.send()
        except Exception:
            pass  # mail stays in queue for cron

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if not vals.get('workflow_level_id'):
                vals['workflow_level_id'] = self._default_workflow_level_id()
            if vals.get('workflow_level_id') and 'workflow_level_since' not in vals:
                vals['workflow_level_since'] = now
        tickets = super(HelpdeskTicket, self).create(vals_list)
        tickets._assign_user_from_branch_workflow()
        return tickets

    def write(self, vals):
        """
        Override write method to detect stage or workflow level changes and call external API.
        Handles automatic workflow level increment for "Approved" stage.
        """
        self._check_workflow_level_downgrade(vals)
        if 'workflow_level_id' in vals and 'workflow_level_since' not in vals:
            vals['workflow_level_since'] = fields.Datetime.now()
        # Track which tickets had stage or workflow level changes
        tickets_to_sync = {}
        
        # Check for stage changes - only call API for "Approved" or "Rejected" stages
        if 'stage_id' in vals:
            new_stage_id = vals['stage_id']
            new_stage = self.env['helpdesk.stage'].browse(new_stage_id)
            new_stage_name = new_stage.name if new_stage.exists() else ''
            
            for ticket in self:
                if ticket.stage_id.id != new_stage_id:
                    new_stage_lower = new_stage_name.strip().lower() if new_stage_name else ''
                    
                    # Only track and call API for "Approved" or "Rejected" stages
                    if new_stage_lower in ['approved', 'rejected']:
                        if ticket.id not in tickets_to_sync:
                            tickets_to_sync[ticket.id] = {}
                        tickets_to_sync[ticket.id]['old_stage_id'] = ticket.stage_id.id
                        tickets_to_sync[ticket.id]['new_stage_id'] = new_stage_id
                        tickets_to_sync[ticket.id]['new_stage_name'] = new_stage_name
                        
                        # If stage changes to "Approved", call API with CURRENT level first, then increment
                        if new_stage_lower == 'approved':
                            current_level = ticket.workflow_level_id
                            current_code = current_level.code if current_level else '1'
                            
                            # Always mark that we need to call API with CURRENT level (regardless of increment)
                            tickets_to_sync[ticket.id]['call_api_with_current_level'] = True
                            tickets_to_sync[ticket.id]['current_level_for_api'] = current_code
                            
                            # Find next workflow level by sequence
                            next_level = self.env['workflow.level'].search([
                                ('sequence', '>', current_level.sequence if current_level else 0)
                            ], order='sequence', limit=1)
                            
                            if next_level and ('workflow_level_id' not in vals or vals['workflow_level_id'] != next_level.id):
                                vals['workflow_level_id'] = next_level.id
                                tickets_to_sync[ticket.id]['workflow_level_auto_incremented'] = True
                                _logger.info(
                                    "Will call API with current level %s, then auto-increment to %s for ticket %s (Approved stage)",
                                    current_code, next_level.code, ticket.name
                                )
                            else:
                                _logger.info(
                                    "Will call API with current level %s (already at max, no increment) for ticket %s (Approved stage)",
                                    current_code, ticket.name
                                )
                        # If stage changes to "Rejected", call API with current workflow level
                        elif new_stage_lower == 'rejected':
                            tickets_to_sync[ticket.id]['call_api_for_rejected'] = True
                            _logger.info(
                                "Will call API for ticket %s (Rejected stage) with current level %s",
                                ticket.name, ticket.workflow_level_id.code if ticket.workflow_level_id else ''
                            )
        
        # Call super to perform the actual write first
        # This ensures the ticket state is committed before API calls
        result = super(HelpdeskTicket, self).write(vals)

        # If ticket has ram_id, assign to user linked to workflow_level_id on branch
        self._assign_user_from_branch_workflow()
        
        # After successful write, call API for "Approved" or "Rejected" stages
        if tickets_to_sync:
            for ticket in self:
                if ticket.id in tickets_to_sync:
                    sync_info = tickets_to_sync[ticket.id]
                    
                    # For "Approved" stage: call API with CURRENT level (before increment)
                    if sync_info.get('call_api_with_current_level'):
                        current_level_for_api = sync_info.get('current_level_for_api', '1')
                        original_level_id = ticket.workflow_level_id
                        _logger.info(
                            "Calling API for Approved stage - ticket %s, current level: %s, ticket workflow_level_id: %s",
                            ticket.name, current_level_for_api, ticket.workflow_level_id.code if ticket.workflow_level_id else ''
                        )
                        try:
                            # Temporarily override workflow_level_id to use current level for API call
                            original_level_id = ticket.workflow_level_id
                            level_for_api = self.env['workflow.level'].search([('code', '=', current_level_for_api)], limit=1)
                            if level_for_api:
                                ticket.with_context(skip_workflow_level_downgrade_check=True).write({
                                    'workflow_level_id': level_for_api.id,
                                })
                            
                            _logger.info(
                                "Making API call with level %s for ticket %s (Approved stage)",
                                current_level_for_api, ticket.name
                            )
                            
                            # Call API with current level and "Approved" status
                            response = ticket._call_ram_api(ticket, status_override='Approved')
                            
                            _logger.info(
                                "API call completed for ticket %s - status: %s, response: %s",
                                ticket.name,
                                response.status_code if response else 'No response',
                                response.text[:100] if response and response.text else 'No text'
                            )
                            
                            # Restore the incremented level
                            if original_level_id:
                                ticket.with_context(skip_workflow_level_downgrade_check=True).write({
                                    'workflow_level_id': original_level_id.id,
                                })
                            
                            # Show success notification for all 2xx status codes (200, 201, 204, etc.)
                            if response and 200 <= response.status_code < 300:
                                ticket._show_notification(
                                    _('API Sync Success'),
                                    _('Ticket %s successfully synced with RAM Prime Care API (Status: %s)') % (ticket.name, response.status_code),
                                    'success'
                                )
                            elif response:
                                ticket._show_notification(
                                    _('API Sync Warning'),
                                    _('Ticket %s synced but API returned status %s') % (ticket.name, response.status_code),
                                    'warning'
                                )
                        except Exception as e:
                            # Restore level even if API call fails
                            if original_level_id:
                                ticket.with_context(skip_workflow_level_downgrade_check=True).write({
                                    'workflow_level_id': original_level_id.id,
                                })
                            _logger.error(
                                "Failed to call RAM API for ticket %s: %s",
                                ticket.name,
                                str(e)
                            )
                            # Show error notification
                            ticket._show_notification(
                                _('API Sync Failed'),
                                _('Failed to sync ticket %s with RAM Prime Care API: %s') % (ticket.name, str(e)),
                                'danger'
                            )
                    
                    # Call API for "Rejected" stage
                    elif sync_info.get('call_api_for_rejected'):
                        try:
                            # Call API with "Rejected" status (not the stage name)
                            response = ticket._call_ram_api(ticket, status_override='Rejected')
                            
                            # Also treat 400 with "Duplicate Workflow Update" as success
                            is_duplicate = (response and response.status_code == 400 and 
                                          response.text and 'Duplicate Workflow Update' in response.text)
                            
                            # Show success notification for all 2xx status codes (200, 201, 204, etc.)
                            if response and (200 <= response.status_code < 300 or is_duplicate):
                                if is_duplicate:
                                    ticket._show_notification(
                                        _('API Sync Info'),
                                        _('Ticket %s: Workflow level already sent to API (duplicate update)') % ticket.name,
                                        'info'
                                    )
                                else:
                                    ticket._show_notification(
                                        _('API Sync Success'),
                                        _('Ticket %s successfully synced with RAM Prime Care API (Status: %s)') % (ticket.name, response.status_code),
                                        'success'
                                    )
                            elif response:
                                ticket._show_notification(
                                    _('API Sync Warning'),
                                    _('Ticket %s synced but API returned status %s') % (ticket.name, response.status_code),
                                    'warning'
                                )
                        except Exception as e:
                            _logger.error(
                                "Failed to call RAM API for ticket %s: %s",
                                ticket.name,
                                str(e)
                            )
                            # Show error notification
                            ticket._show_notification(
                                _('API Sync Failed'),
                                _('Failed to sync ticket %s with RAM Prime Care API: %s') % (ticket.name, str(e)),
                                'danger'
                            )
                        # Don't block the ticket update if API call fails
        
        return result

    def _call_ram_api(self, ticket, status_override=None):
        """
        Call RAM Prime Care API with ticket information.
        
        URL format: http://15.184.10.121:8080/HISAdmin/api/odooIntegration/updateRefundTask/
                    {{ticketId}}/{{workFlowLevel}}/{{status}}/{{updateTime}}
        
        :param ticket: helpdesk.ticket record
        """
        # Get configuration from system parameters
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        bearer_token = IrConfigParam.get_param('top_ram_api.bearer_token', default='')
        base_url = IrConfigParam.get_param(
            'top_ram_api.endpoint',
            default='http://15.184.10.121:8080/HISAdmin/api/odooIntegration/updateRefundTask/'
        )
        # Get timeout from system parameters (default: 60 seconds)
        timeout = int(IrConfigParam.get_param('top_ram_api.timeout', default='60'))
        
        if not bearer_token:
            _logger.warning("Bearer token not configured in system parameters (top_ram_api.bearer_token)")
            # You can choose to raise an error or continue without token
            # raise UserError(_("RAM API Bearer token not configured. Please contact administrator."))
        
        # Prepare parameters
        ticket_id = ticket.ram_id or ''
        workflow_level = ticket.workflow_level_id.code if ticket.workflow_level_id else '1'
        refund_reason = ticket.refund_reason or ''

        # Use status_override if provided (for Approved/Rejected), otherwise use stage name
        if status_override:
            status = status_override
        else:
            status = ticket.stage_id.name if ticket.stage_id else ''
        
        # Build URL with new format: {base_url}/{ram_id}/{workflow_level}/{stage_name}?comment={reason}
        # Strip trailing slash from base_url if present
        base_url = base_url.rstrip('/')
        
        # Build path parameters
        path_parts = [
            quote(str(ticket_id), safe=''),
            quote(str(workflow_level), safe=''),
            quote(str(status), safe=''),
        ]
        path_url = f"{base_url}/" + "/".join(path_parts)
        
        # Build query parameter for comment
        query_params = {'comment': refund_reason} if refund_reason else {}
        query_string = urlencode(query_params) if query_params else ''
        
        # Combine path and query
        api_url = f"{path_url}?{query_string}" if query_string else path_url
        
        # Log the URL construction details for debugging
        _logger.info("=== RAM API URL Construction ===")
        _logger.info("Base URL: %s", base_url)
        _logger.info("RAM ID: %s", ticket_id)
        _logger.info("Workflow Level: %s", workflow_level)
        _logger.info("Stage Name (raw): %s", status)
        _logger.info("Stage Name (encoded): %s", quote(str(status), safe=''))
        _logger.info("Comment/Reason (raw): %s", refund_reason)
        _logger.info("Comment/Reason (encoded): %s", quote(str(refund_reason), safe=''))
        _logger.info("Final URL: %s", api_url)
        _logger.info("================================")
        
        # Prepare headers with Bearer token
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        _logger.info("Calling RAM API: %s (with Bearer token)", api_url)
        
        response = None
        exception_obj = None
        error_message = None
        
        try:
            # Make HTTP GET request with Bearer token
            # Timeout is configurable via system parameter 'top_ram_api.timeout' (default: 60 seconds)
            response = requests.get(api_url, headers=headers, timeout=timeout)
            
            # Log response - treat all 2xx status codes as success (200, 201, 204, etc.)
            if 200 <= response.status_code < 300:
                _logger.info(
                    "RAM API call successful for ticket %s (status %s). Response: %s",
                    ticket.name,
                    response.status_code,
                    response.text if response.text else "(No content)"
                )
            else:
                # Non-2xx status codes are treated as errors
                # Provide specific messages for common error codes
                response_text = response.text if response.text else ''
                
                # Check for duplicate workflow update (400 error with specific message)
                if response.status_code == 400 and 'Duplicate Workflow Update' in response_text:
                    # This is not really an error - the workflow level was already updated
                    # Treat it as a success/info message
                    _logger.info(
                        "RAM API returned duplicate workflow update for ticket %s (level already sent). Response: %s",
                        ticket.name,
                        response_text[:200]
                    )
                    # Set error_message to None so it's treated as success
                    error_message = None
                elif response.status_code == 404:
                    error_message = f"404 Not Found: The API endpoint was not found. Please verify the endpoint URL and path parameters. Response: {response_text[:200] if response_text else 'No response body'}"
                elif response.status_code == 401:
                    error_message = f"401 Unauthorized: Authentication failed. Please check the Bearer token. Response: {response_text[:200] if response_text else 'No response body'}"
                elif response.status_code == 403:
                    error_message = f"403 Forbidden: Access denied. Please check permissions. Response: {response_text[:200] if response_text else 'No response body'}"
                elif response.status_code == 500:
                    error_message = f"500 Internal Server Error: The API server encountered an error. Response: {response_text[:200] if response_text else 'No response body'}"
                else:
                    error_message = f"API returned status code {response.status_code}: {response_text[:200] if response_text else 'No response body'}"
                
                _logger.warning(
                    "RAM API call returned status %s for ticket %s. Response: %s",
                    response.status_code,
                    ticket.name,
                    response.text if response.text else "(No content)"
                )
                
        except requests.exceptions.Timeout:
            exception_obj = requests.exceptions.Timeout(f"Request timeout after {timeout} seconds")
            error_message = f"Request timeout: The API server did not respond within {timeout} seconds"
            _logger.error("RAM API call timeout for ticket %s (timeout: %s seconds)", ticket.name, timeout)
        except requests.exceptions.ConnectionError as e:
            exception_obj = e
            error_message = f"Connection error: Unable to connect to the API server. {str(e)}"
            _logger.error("RAM API connection error for ticket %s: %s", ticket.name, str(e))
        except requests.exceptions.RequestException as e:
            exception_obj = e
            error_message = f"Request error: {str(e)}"
            _logger.error("RAM API request error for ticket %s: %s", ticket.name, str(e))
        except Exception as e:
            exception_obj = e
            error_message = f"Unexpected error: {str(e)}"
            _logger.error("RAM API call failed for ticket %s: %s", ticket.name, str(e), exc_info=True)
            
            
        # Post request/response details to chatter for traceability
        # We do this regardless of success or failure to ensure visibility
        try:
            # Try to parse JSON response if possible
            response_text = ''
            response_json = None
            is_duplicate_update = False
            
            if response:
                response_text = response.text
                # Check for duplicate workflow update (400 error with specific message)
                is_duplicate_update = (response.status_code == 400 and 
                                     response_text and 'Duplicate Workflow Update' in response_text)
                try:
                    # Try to parse as JSON for pretty formatting
                    response_json = response.json()
                except (ValueError, json.JSONDecodeError):
                    # Not JSON, use text as-is
                    pass
            
            request_details = {
                "url": api_url,
                "params": {
                    "ram_id": ticket_id,
                    "workflow_level": workflow_level,
                    "stage_name": status,
                    "comment": refund_reason
                },
                "headers": {
                    # Mask token for security
                    "Authorization": "Bearer ****",
                    "Content-Type": headers.get("Content-Type"),
                    "Accept": headers.get("Accept"),
                },
                "response": {
                    "status_code": response.status_code if response else "N/A",
                    "text": response_text if response else str(exception_obj),
                    "json": response_json if response_json else None,
                },
            }
            
            # Treat duplicate workflow update (400) as success since it means the level was already sent
            if response and (200 <= response.status_code < 300 or is_duplicate_update):
                # Format the response body - use JSON if available, otherwise use text
                # Handle 204 No Content which has no response body
                if response.status_code == 204:
                    response_display = "<p><em>No Content (204) - Request successful but no response body</em></p>"
                elif response_json:
                    formatted_response = json.dumps(response_json, indent=2, ensure_ascii=False)
                    response_display = f"<pre style='white-space: pre-wrap;'>{formatted_response}</pre>"
                elif response_text:
                    # Escape HTML and preserve formatting
                    escaped_text = escape(response_text)
                    response_display = f"<pre style='white-space: pre-wrap;'>{escaped_text}</pre>"
                else:
                    response_display = "<p><em>Empty response body</em></p>"
                
                # Format the body to clearly show the response log
                status_label = "Success" if not is_duplicate_update else "Info (Duplicate Update)"
                status_color = "green" if not is_duplicate_update else "blue"
                status_icon = "✅" if not is_duplicate_update else "ℹ️"
                
                if is_duplicate_update:
                    response_display = "<p><em>Duplicate Workflow Update: This workflow level has already been sent to the API. No action needed.</em></p>"
                
                body_content = (
                    f"<p><strong>{status_icon} RAM API Response Log ({status_label})</strong></p>"
                    f"<p><strong>Status Code:</strong> <span style='color: {status_color}; font-weight: bold;'>{response.status_code}</span></p>"
                    f"<p><strong>Response Body:</strong></p>"
                    f"{response_display}"
                    f"<details style='margin-top: 10px;'>"
                    f"<summary style='cursor: pointer; color: #666;'><strong>📋 View Full Request Details</strong></summary>"
                    f"<p style='margin-top: 10px;'><strong>Endpoint URL:</strong><br/><code style='background: #f5f5f5; padding: 5px; display: block; word-break: break-all;'>{api_url}</code></p>"
                    f"<p><strong>Request Parameters (Raw Values):</strong></p>"
                    f"<ul>"
                    f"<li><strong>RAM ID:</strong> <code>{ticket_id}</code></li>"
                    f"<li><strong>Workflow Level:</strong> <code>{workflow_level}</code></li>"
                    f"<li><strong>Stage Name (raw):</strong> <code>'{status}'</code> (length: {len(status)})</li>"
                    f"<li><strong>Stage Name (encoded):</strong> <code>{quote(str(status), safe='')}</code></li>"
                    f"<li><strong>Comment/Reason (raw):</strong> <code>'{refund_reason or 'N/A'}'</code></li>"
                    f"<li><strong>Comment/Reason (encoded):</strong> <code>{quote(str(refund_reason), safe='') if refund_reason else 'N/A'}</code></li>"
                    f"</ul>"
                    f"<p><strong>URL Format:</strong></p>"
                    f"<code style='background: #f5f5f5; padding: 5px; display: block; word-break: break-all;'>{base_url.rstrip('/')}/{ticket_id}/{workflow_level}/{quote(str(status), safe='')}?comment={quote(str(refund_reason), safe='') if refund_reason else ''}</code>"
                    f"</details>"
                )
            else:
                # Format for error case - either no response or non-200 status code
                # Use error_message if available, otherwise use exception_obj, otherwise use response status
                if error_message:
                    display_error = error_message
                elif exception_obj:
                    display_error = str(exception_obj)
                elif response:
                    display_error = f"API returned status code {response.status_code}: {response_text[:200] if response_text else 'No response body'}"
                else:
                    display_error = "Unknown error: No response received from API server"
                
                error_msg = escape(display_error)
                body_content = (
                    f"<p><strong>❌ RAM API Call Failed</strong></p>"
                    f"<p><strong>Error:</strong></p>"
                    f"<pre style='white-space: pre-wrap; color: red;'>{error_msg}</pre>"
                    f"<details style='margin-top: 10px;'>"
                    f"<summary style='cursor: pointer; color: #666;'><strong>📋 View Request Details</strong></summary>"
                    f"<p style='margin-top: 10px;'><strong>Endpoint URL:</strong><br/><code style='background: #f5f5f5; padding: 5px; display: block; word-break: break-all;'>{api_url}</code></p>"
                    f"<p><strong>Request Parameters (Raw Values):</strong></p>"
                    f"<ul>"
                    f"<li><strong>RAM ID:</strong> <code>{ticket_id}</code></li>"
                    f"<li><strong>Workflow Level:</strong> <code>{workflow_level}</code></li>"
                    f"<li><strong>Stage Name (raw):</strong> <code>'{status}'</code> (length: {len(status)})</li>"
                    f"<li><strong>Stage Name (encoded):</strong> <code>{quote(str(status), safe='')}</code></li>"
                    f"<li><strong>Comment/Reason (raw):</strong> <code>'{refund_reason or 'N/A'}'</code></li>"
                    f"<li><strong>Comment/Reason (encoded):</strong> <code>{quote(str(refund_reason), safe='') if refund_reason else 'N/A'}</code></li>"
                    f"</ul>"
                    f"<p><strong>URL Breakdown:</strong></p>"
                    f"<code style='background: #f5f5f5; padding: 5px; display: block; word-break: break-all;'>{base_url.rstrip('/')}/{ticket_id}/{workflow_level}/{quote(str(status), safe='')}?comment={quote(str(refund_reason), safe='') if refund_reason else ''}</code>"
                    f"</details>"
                )
            
            # Post to chatter - use sudo() to ensure permissions, with_context to prevent duplicate logging
            msg = ticket.sudo().with_context(mail_create_nolog=False).message_post(
                body=body_content,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            _logger.info(
                "Successfully posted RAM API response to chatter for ticket %s (message ID: %s)",
                ticket.name,
                msg.id if hasattr(msg, 'id') else 'unknown'
            )
        except Exception as post_e:
            _logger.error(
                "Failed to post RAM API details to chatter for ticket %s: %s",
                ticket.name if 'ticket' in locals() else 'unknown',
                str(post_e),
                exc_info=True
            )
            # Try one more time with simpler approach as fallback
            try:
                if 'ticket' in locals() and 'body_content' in locals():
                    ticket.sudo().message_post(body=body_content, message_type='notification')
                    _logger.info("Posted RAM API response using fallback method for ticket %s", ticket.name)
            except Exception as fallback_error:
                _logger.error("Fallback message_post also failed: %s", str(fallback_error), exc_info=True)
        
        # If there was an exception during the API call, re-raise it now
        # so the caller knows it failed (and can show the toast notification)
        # Note: Non-200 status codes are not raised as exceptions, they're logged as warnings
        if exception_obj:
            raise exception_obj
            
        return response

    def _show_notification(self, title, message, notification_type='info'):
        """
        Display toast notification to the user.
        
        :param title: Notification title
        :param message: Notification message
        :param notification_type: Type of notification (success, warning, danger, info)
        """
        self.ensure_one()
        
        # Map notification types to Odoo notification types
        type_mapping = {
            'success': 'success',
            'warning': 'warning',
            'danger': 'danger',
            'info': 'info',
        }
        
        odoo_type = type_mapping.get(notification_type, 'info')
        
        # Method 1: Send notification via bus (Odoo 18 format)
        try:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': title,
                    'message': message,
                    'type': odoo_type,
                    'sticky': False,
                }
            )
        except Exception as e:
            _logger.warning("Failed to send bus notification: %s", str(e))
        
        # Method 2: Post message in ticket chatter (always works)
        # Choose icon based on notification type
        icon = {
            'success': '✅',
            'warning': '⚠️',
            'danger': '🚫',
            'info': 'ℹ️',
        }.get(notification_type, 'ℹ️')
        
        # Post message to ticket
        self.message_post(
            body=f"<p><strong>{icon} {title}</strong></p><p>{message}</p>",
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def _notify_team_members(self):
        """
        Override ramcrm: push notification only to the assigned user, not to all team members.
        """
        for ticket in self:
            if not ticket.user_id:
                continue
            self.env['mail.activity'].create({
                'display_name': 'New Ticket',
                'summary': 'New Ticket',
                'date_deadline': datetime.now(),
                'user_id': ticket.user_id.id,
                'res_model_id': self.env.ref('helpdesk.model_helpdesk_ticket').id,
                'res_id': ticket.id,
            })
