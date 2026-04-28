from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class TicketTeamAssignmentRule(models.Model):
    _name = 'clinizone.ticket_team_assignment_rule'
    _description = 'Ticket Team Assignment Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True, help='Uncheck to disable this assignment rule')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    sequence = fields.Integer(string='Sequence', default=10, help='Rules are evaluated in ascending order of sequence')
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string='Ticket Type', required=False,
                                     help='Leave empty to match all ticket types, or specify a specific ticket type')
    case_source_id = fields.Many2one('clinizone.ram_case_source', string='Case Source', required=False,
                                     help='Leave empty to match all case sources, or specify a specific case source')
    branch_is_defined = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Branch is Defined', required=False,
       help='Leave empty to match both cases, or specify if branch must be defined or not')
    assignment_type = fields.Selection([
        ('specific', 'Specific Team'),
        ('branch', "Branch's Helpdesk Team"),
        ('branch_medical_director', "Branch's Medical Director Team"),
    ], string='Assignment Type', required=True,
       help='How to determine the team assignment')
    team_id = fields.Many2one('helpdesk.team', string='Team',
                              help='Required when Assignment Type is "Specific Team"')

    def evaluate(self, ticket_type_id, branch_id, case_source_id):
        """
        Evaluate if this rule matches the given ticket criteria and return the team ID.
        
        :param ticket_type_id: ID of the ticket type
        :param branch_id: ID of the branch (can be None)
        :param case_source_id: ID of the case source (can be None)
        :return: Team ID if rule matches, False otherwise
        :raises UserError: If required data is missing for assignment
        """
        # Check if branch_is_defined condition matches
        branch_is_defined_match = (
            not self.branch_is_defined or
            (self.branch_is_defined == 'yes' and branch_id) or
            (self.branch_is_defined == 'no' and not branch_id)
        )
        
        # Check if ticket_type matches (empty ticket_type_id means match all)
        # Handle both integer ID and tuple (id, name) format
        rule_ticket_type_id = self.ticket_type_id.id if self.ticket_type_id else None
        if isinstance(ticket_type_id, (list, tuple)):
            ticket_type_id = ticket_type_id[0] if ticket_type_id else None
        
        ticket_type_match = (
            not rule_ticket_type_id or
            (ticket_type_id and rule_ticket_type_id == ticket_type_id)
        )
        
        # Check if case_source matches (empty case_source_id means match all)
        # Handle both integer ID and tuple (id, name) format
        rule_case_source_id = self.case_source_id.id if self.case_source_id else None
        if isinstance(case_source_id, (list, tuple)):
            case_source_id = case_source_id[0] if case_source_id else None
        
        case_source_match = (
            not rule_case_source_id or
            (case_source_id and rule_case_source_id == case_source_id)
        )
        
        # If any condition doesn't match, this rule doesn't apply
        if not (branch_is_defined_match and ticket_type_match and case_source_match):
            return False
        
        # All conditions match, now determine the team based on assignment_type
        if self.assignment_type == 'specific':
            if not self.team_id:
                raise UserError(_('Team is not defined for rule: %s') % self.name)
            return self.team_id.id
            
        elif self.assignment_type == 'branch':
            if not branch_id:
                raise UserError(_('Branch is required for rule: %s') % self.name)
            branch = self.env['clinizone.branch'].browse(branch_id)
            if not branch.exists():
                raise UserError(_('Branch not found for rule: %s') % self.name)
            if not branch.helpdesk_team_id:
                raise UserError(_('Branch "%s" does not have a helpdesk team configured') % branch.name)
            return branch.helpdesk_team_id.id
            
        elif self.assignment_type == 'branch_medical_director':
            if not branch_id:
                raise UserError(_('Branch is required for rule: %s') % self.name)
            branch = self.env['clinizone.branch'].browse(branch_id)
            if not branch.exists():
                raise UserError(_('Branch not found for rule: %s') % self.name)
            if not branch.medical_director_team_id:
                raise UserError(_('Branch "%s" does not have a medical director team configured') % branch.name)
            return branch.medical_director_team_id.id
            
        return False

    @api.model
    def _column_exists(self, table_name, column_name):
        """
        Check if a column exists in the database table.
        
        :param table_name: Name of the table (will be converted to lowercase)
        :param column_name: Name of the column (will be converted to lowercase)
        :return: True if column exists, False otherwise
        """
        try:
            # Use LOWER() for case-insensitive comparison (PostgreSQL table/column names are case-sensitive)
            self.env.cr.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE LOWER(table_name) = LOWER(%s) AND LOWER(column_name) = LOWER(%s)
            """, (table_name, column_name))
            return bool(self.env.cr.fetchone())
        except Exception:
            # If check fails, assume column doesn't exist to be safe
            return False

    @api.model
    def compute_team(self, ticket_type_id, branch_id, case_source_id):
        """
        Compute and return the appropriate team ID based on configured assignment rules.
        
        Rules are evaluated in order of sequence. The first matching rule determines the team.
        Only active rules for the current company are considered.
        
        :param ticket_type_id: ID of the ticket type (can be None)
        :param branch_id: ID of the branch (can be None)
        :param case_source_id: ID of the case source (can be None)
        :return: Team ID if a matching rule is found, False otherwise
        """
        if not ticket_type_id:
            _logger.warning('compute_team called without ticket_type_id')
            return False
            
        # Search for active rules for the current company, ordered by sequence
        # Handle case where 'active' column might not exist yet (before module upgrade)
        domain = [('company_id', '=', self.env.company.id)]
        
        # Check if 'active' column exists in database before using it
        # This prevents transaction abort errors by checking before querying
        table_name = self._table.replace('"', '').replace("'", '')
        if self._column_exists(table_name, 'active'):
            domain.append(('active', '=', True))
        else:
            _logger.debug('Active column not found in database table %s. Searching all rules. Please upgrade the module.', table_name)
        
        rules = self.search(domain, order='sequence, id')
        
        if not rules:
            _logger.info('No assignment rules found for company: %s', self.env.company.name)
            return False
        
        # Evaluate each rule in sequence until one matches
        _logger.debug('Evaluating %d rules for ticket_type_id=%s, branch_id=%s, case_source_id=%s',
                     len(rules), ticket_type_id, branch_id, case_source_id)
        
        for rule in rules:
            try:
                _logger.debug('Evaluating rule "%s" (sequence=%s, ticket_type=%s, case_source=%s, branch_is_defined=%s, assignment_type=%s)',
                             rule.name, rule.sequence, rule.ticket_type_id.name if rule.ticket_type_id else 'Any',
                             rule.case_source_id.name if rule.case_source_id else 'Any',
                             rule.branch_is_defined or 'Any', rule.assignment_type)
                
                team_id = rule.evaluate(ticket_type_id, branch_id, case_source_id)
                if team_id:
                    _logger.info('✓ Rule "%s" (sequence=%s) matched and assigned team ID: %s', rule.name, rule.sequence, team_id)
                    return team_id
                else:
                    _logger.debug('✗ Rule "%s" did not match', rule.name)
            except UserError:
                # Re-raise UserError as it contains important validation messages
                raise
            except Exception as e:
                _logger.exception('Error evaluating rule "%s": %s', rule.name, str(e))
                # Continue to next rule if evaluation fails
                continue
        
        _logger.warning('No matching assignment rule found for ticket_type_id=%s, branch_id=%s, case_source_id=%s. Total rules evaluated: %d',
                     ticket_type_id, branch_id, case_source_id, len(rules))
        return False