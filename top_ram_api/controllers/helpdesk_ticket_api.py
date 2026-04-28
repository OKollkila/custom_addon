from odoo import http, fields
from odoo.http import request, Response
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class HelpdeskTicketAPIController(http.Controller):
    """
    API Controller for Helpdesk Tickets with RAM ID.
    
    Provides endpoints to retrieve helpdesk ticket data filtered by date range
    where ram_id is not empty.
    
    Authentication: Bearer Token
    - Token should be configured in System Parameters: 'top_ram_api.api_access_token'
    - Pass token in Authorization header: 'Authorization: Bearer <token>'
    """

    def _validate_bearer_token(self):
        """
        Validate Bearer token from Authorization header.
        
        Returns:
            tuple: (is_valid: bool, error_response: Response or None)
        """
        auth_header = request.httprequest.headers.get('Authorization', '')
        
        if not auth_header:
            return False, self._json_response({
                'success': False,
                'error': 'Missing Authorization header. Use: Authorization: Bearer <token>'
            }, status=401)
        
        # Check if it's a Bearer token
        if not auth_header.startswith('Bearer '):
            return False, self._json_response({
                'success': False,
                'error': 'Invalid Authorization format. Use: Authorization: Bearer <token>'
            }, status=401)
        
        # Extract token
        token = auth_header[7:].strip()  # Remove 'Bearer ' prefix
        
        if not token:
            return False, self._json_response({
                'success': False,
                'error': 'Empty Bearer token'
            }, status=401)
        
        # Get configured token from system parameters
        IrConfigParam = request.env['ir.config_parameter'].sudo()
        configured_token = IrConfigParam.get_param('top_ram_api.api_access_token', default='')
        
        if not configured_token:
            _logger.error("API access token not configured in system parameters (top_ram_api.api_access_token)")
            return False, self._json_response({
                'success': False,
                'error': 'API authentication not configured. Contact administrator.'
            }, status=500)
        
        # Validate token
        if token != configured_token:
            _logger.warning("Invalid API access token attempt")
            return False, self._json_response({
                'success': False,
                'error': 'Invalid Bearer token'
            }, status=401)
        
        return True, None

    @http.route(
        '/api/v1/helpdesk/tickets/ram',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_ram_tickets(self, date_from=None, date_to=None, **kwargs):
        """
        Get all helpdesk tickets where ram_id is not empty, filtered by custom date range.
        
        Query Parameters:
            date_from (str): Start date in format 'YYYY-MM-DD' (optional)
            date_to (str): End date in format 'YYYY-MM-DD' (optional)
        
        Returns:
            JSON response with ticket data including:
            - ram_id
            - invid
            - refund_reason
            - workflow_level
            - All related ticket data
        
        Example:
            GET /api/v1/helpdesk/tickets/ram?date_from=2026-01-01&date_to=2026-01-31
        """
        # Validate bearer token
        is_valid, error_response = self._validate_bearer_token()
        if not is_valid:
            return error_response
        
        try:
            # Build domain filter
            domain = [
                ('ram_id', '!=', False),
                ('ram_id', '!=', ''),
            ]
            
            # Add date filters if provided
            if date_from:
                try:
                    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d')
                    domain.append(('create_date', '>=', date_from_parsed.strftime('%Y-%m-%d 00:00:00')))
                except ValueError:
                    return self._json_response({
                        'success': False,
                        'error': 'Invalid date_from format. Use YYYY-MM-DD'
                    }, status=400)
            
            if date_to:
                try:
                    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d')
                    domain.append(('create_date', '<=', date_to_parsed.strftime('%Y-%m-%d 23:59:59')))
                except ValueError:
                    return self._json_response({
                        'success': False,
                        'error': 'Invalid date_to format. Use YYYY-MM-DD'
                    }, status=400)
            
            # Fetch tickets
            tickets = request.env['helpdesk.ticket'].sudo().search(domain, order='create_date desc')
            
            # Prepare response data
            tickets_data = []
            for ticket in tickets:
                ticket_data = self._serialize_ticket(ticket)
                tickets_data.append(ticket_data)
            
            return self._json_response({
                'success': True,
                'count': len(tickets_data),
                'date_from': date_from,
                'date_to': date_to,
                'tickets': tickets_data
            })
            
        except Exception as e:
            _logger.error("Error fetching RAM tickets: %s", str(e), exc_info=True)
            return self._json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    @http.route(
        '/api/v1/helpdesk/tickets/ram/<int:ticket_id>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_ram_ticket_by_id(self, ticket_id, **kwargs):
        """
        Get a specific helpdesk ticket by ID where ram_id is not empty.
        
        Path Parameters:
            ticket_id (int): The ticket ID
        
        Returns:
            JSON response with complete ticket data
        """
        # Validate bearer token
        is_valid, error_response = self._validate_bearer_token()
        if not is_valid:
            return error_response
        
        try:
            ticket = request.env['helpdesk.ticket'].sudo().search([
                ('id', '=', ticket_id),
                ('ram_id', '!=', False),
                ('ram_id', '!=', ''),
            ], limit=1)
            
            if not ticket:
                return self._json_response({
                    'success': False,
                    'error': 'Ticket not found or has no RAM ID'
                }, status=404)
            
            return self._json_response({
                'success': True,
                'ticket': self._serialize_ticket(ticket)
            })
            
        except Exception as e:
            _logger.error("Error fetching RAM ticket %s: %s", ticket_id, str(e), exc_info=True)
            return self._json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    def _serialize_ticket(self, ticket):
        """
        Serialize a helpdesk ticket to a dictionary with all relevant data.
        
        :param ticket: helpdesk.ticket record
        :return: Dictionary with ticket data
        """
        # Get workflow level display value
        workflow_level_display = dict(ticket._fields['workflow_level'].selection).get(
            ticket.workflow_level, ticket.workflow_level
        ) if ticket.workflow_level else None
        
        # Build the response with required fields and related data
        data = {
            # Primary requested fields
            'ram_id': ticket.ram_id or '',
            'invid': ticket.invid or '',
            'refund_reason': ticket.refund_reason or '',
            'workflow_level': ticket.workflow_level or '',
            'workflow_level_display': workflow_level_display,
            
            # Ticket base information
            'id': ticket.id,
            'name': ticket.name or '',
            'description': ticket.description or '',
            'priority': ticket.priority or '0',
            
            # Dates
            'create_date': ticket.create_date.isoformat() if ticket.create_date else None,
            'write_date': ticket.write_date.isoformat() if ticket.write_date else None,
            
            # Stage information
            'stage_id': ticket.stage_id.id if ticket.stage_id else None,
            'stage_name': ticket.stage_id.name if ticket.stage_id else None,
            
            # Ticket type
            'ticket_type_id': ticket.ticket_type_id.id if ticket.ticket_type_id else None,
            'ticket_type_name': ticket.ticket_type_id.name if ticket.ticket_type_id else None,
            
            # Team information
            'team_id': ticket.team_id.id if ticket.team_id else None,
            'team_name': ticket.team_id.name if ticket.team_id else None,
            
            # Partner (Customer) information
            'partner_id': ticket.partner_id.id if ticket.partner_id else None,
            'partner_name': ticket.partner_id.name if ticket.partner_id else None,
            'partner_email': ticket.partner_id.email if ticket.partner_id else None,
            'partner_phone': ticket.partner_id.phone if ticket.partner_id else None,
            
            # Assigned user information
            'user_id': ticket.user_id.id if ticket.user_id else None,
            'user_name': ticket.user_id.name if ticket.user_id else None,
            
            # SLA information (if available)
            'sla_deadline': ticket.sla_deadline.isoformat() if hasattr(ticket, 'sla_deadline') and ticket.sla_deadline else None,
            'sla_reached': ticket.sla_reached if hasattr(ticket, 'sla_reached') else None,
            
            # Rating (if available)
            'rating_last_value': ticket.rating_last_value if hasattr(ticket, 'rating_last_value') else None,
            
            # Tags
            'tag_ids': [{'id': tag.id, 'name': tag.name} for tag in ticket.tag_ids] if ticket.tag_ids else [],
        }
        
        return data

    def _json_response(self, data, status=200):
        """
        Create a JSON HTTP response.
        
        :param data: Dictionary to convert to JSON
        :param status: HTTP status code
        :return: HTTP Response with JSON content
        """
        return Response(
            json.dumps(data, default=str, ensure_ascii=False),
            status=status,
            content_type='application/json; charset=utf-8'
        )
