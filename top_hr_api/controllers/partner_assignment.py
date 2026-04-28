# -*- coding: utf-8 -*-

import json
import logging
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


def error_response(error, message):
    """Helper function to create error responses"""
    return {
        'error': True,
        'error_message': message,
        'error_details': str(error)
    }


def success_response(data, message="Success"):
    """Helper function to create success responses"""
    return {
        'success': True,
        'message': message,
        'data': data
    }


class PartnerAssignmentAPI(http.Controller):
    
    @http.route('/api/partner/assignment/<int:parent_partner_id>', 
                type='http', 
                auth='user', 
                methods=['GET'], 
                csrf=False)
    def get_partner_assignments(self, parent_partner_id, **kwargs):
        """
        Get all Partner Assignment contacts under a specific parent partner
        
        Args:
            parent_partner_id (int): ID of the parent partner/company
            
        Returns:
            JSON response with list of partner assignments
        """
        try:
            # Validate parent partner exists
            parent_partner = request.env['res.partner'].browse(parent_partner_id)
            if not parent_partner.exists():
                return request.make_response(
                    json.dumps(error_response(None, f"Parent partner with ID {parent_partner_id} not found")),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Get all child contacts under the parent partner
            child_partners = request.env['res.partner'].search([
                ('parent_id', '=', parent_partner_id),
                ('is_company', '=', False)  # Only get contacts, not companies
            ])
            
            # Prepare response data
            assignments_data = []
            for partner in child_partners:
                assignment_data = {
                    'id': partner.id,
                    'name': partner.name,
                    'email': partner.email or '',
                    'phone': partner.phone or '',
                    'mobile': partner.mobile or '',
                    'title': partner.title.name if partner.title else '',
                    'function': partner.function or '',
                    'parent_partner_id': parent_partner_id,
                    'parent_partner_name': parent_partner.name,
                    'geolocation': {
                        'latitude': partner.partner_latitude or 0.0,
                        'longitude': partner.partner_longitude or 0.0,
                        'accuracy_distance': partner.geolocation_accuracy_distance or 0.0,
                        'has_geolocation': bool(partner.partner_latitude and partner.partner_longitude)
                    },
                    'address': {
                        'street': partner.street or '',
                        'street2': partner.street2 or '',
                        'city': partner.city or '',
                        'state': partner.state_id.name if partner.state_id else '',
                        'zip': partner.zip or '',
                        'country': partner.country_id.name if partner.country_id else ''
                    },
                    'active': partner.active,
                    'create_date': partner.create_date.isoformat() if partner.create_date else '',
                    'write_date': partner.write_date.isoformat() if partner.write_date else ''
                }
                assignments_data.append(assignment_data)
            
            # Prepare response
            response_data = {
                'parent_partner': {
                    'id': parent_partner.id,
                    'name': parent_partner.name,
                    'is_company': parent_partner.is_company
                },
                'assignments': assignments_data,
                'total_count': len(assignments_data),
                'has_geolocation_count': len([p for p in child_partners if p.partner_latitude and p.partner_longitude])
            }
            
            return request.make_response(
                json.dumps(success_response(response_data, f"Found {len(assignments_data)} partner assignments")),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.error(f"Error getting partner assignments: {str(e)}")
            return request.make_response(
                json.dumps(error_response(e, "Failed to get partner assignments")),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/api/partner/assignment/search', 
                type='http', 
                auth='user', 
                methods=['GET'], 
                csrf=False)
    def search_partner_assignments(self, **kwargs):
        """
        Search partner assignments with filters
        
        Query Parameters:
            parent_partner_id (int): Filter by parent partner ID
            has_geolocation (bool): Filter by geolocation availability
            accuracy_threshold (float): Filter by accuracy distance threshold
            city (str): Filter by city
            state (str): Filter by state
            country (str): Filter by country
            limit (int): Limit number of results (default: 100)
            offset (int): Offset for pagination (default: 0)
        """
        try:
            # Parse query parameters
            parent_partner_id = kwargs.get('parent_partner_id')
            has_geolocation = kwargs.get('has_geolocation', '').lower() in ('true', '1', 'yes')
            accuracy_threshold = float(kwargs.get('accuracy_threshold', 0))
            city = kwargs.get('city', '').strip()
            state = kwargs.get('state', '').strip()
            country = kwargs.get('country', '').strip()
            limit = int(kwargs.get('limit', 100))
            offset = int(kwargs.get('offset', 0))
            
            # Build domain
            domain = [('is_company', '=', False)]  # Only contacts
            
            if parent_partner_id:
                domain.append(('parent_id', '=', int(parent_partner_id)))
            
            if has_geolocation:
                domain.extend([
                    ('partner_latitude', '!=', False),
                    ('partner_longitude', '!=', False)
                ])
            
            if accuracy_threshold > 0:
                domain.append(('geolocation_accuracy_distance', '<=', accuracy_threshold))
            
            if city:
                domain.append(('city', 'ilike', city))
            
            if state:
                domain.append(('state_id.name', 'ilike', state))
            
            if country:
                domain.append(('country_id.name', 'ilike', country))
            
            # Search partners
            partners = request.env['res.partner'].search(domain, limit=limit, offset=offset)
            
            # Prepare response data
            assignments_data = []
            for partner in partners:
                assignment_data = {
                    'id': partner.id,
                    'name': partner.name,
                    'email': partner.email or '',
                    'phone': partner.phone or '',
                    'mobile': partner.mobile or '',
                    'title': partner.title.name if partner.title else '',
                    'function': partner.function or '',
                    'parent_partner_id': partner.parent_id.id if partner.parent_id else None,
                    'parent_partner_name': partner.parent_id.name if partner.parent_id else '',
                    'geolocation': {
                        'latitude': partner.partner_latitude or 0.0,
                        'longitude': partner.partner_longitude or 0.0,
                        'accuracy_distance': partner.geolocation_accuracy_distance or 0.0,
                        'has_geolocation': bool(partner.partner_latitude and partner.partner_longitude)
                    },
                    'address': {
                        'street': partner.street or '',
                        'street2': partner.street2 or '',
                        'city': partner.city or '',
                        'state': partner.state_id.name if partner.state_id else '',
                        'zip': partner.zip or '',
                        'country': partner.country_id.name if partner.country_id else ''
                    },
                    'active': partner.active,
                    'create_date': partner.create_date.isoformat() if partner.create_date else '',
                    'write_date': partner.write_date.isoformat() if partner.write_date else ''
                }
                assignments_data.append(assignment_data)
            
            # Get total count for pagination
            total_count = request.env['res.partner'].search_count(domain)
            
            # Prepare response
            response_data = {
                'assignments': assignments_data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                },
                'filters_applied': {
                    'parent_partner_id': parent_partner_id,
                    'has_geolocation': has_geolocation,
                    'accuracy_threshold': accuracy_threshold,
                    'city': city,
                    'state': state,
                    'country': country
                }
            }
            
            return request.make_response(
                json.dumps(success_response(response_data, f"Found {len(assignments_data)} partner assignments")),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.error(f"Error searching partner assignments: {str(e)}")
            return request.make_response(
                json.dumps(error_response(e, "Failed to search partner assignments")),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/api/partner/assignment/<int:partner_id>/geolocation', 
                type='http', 
                auth='user', 
                methods=['GET'], 
                csrf=False)
    def get_partner_geolocation(self, partner_id, **kwargs):
        """
        Get geolocation information for a specific partner
        
        Args:
            partner_id (int): ID of the partner
            
        Returns:
            JSON response with geolocation data
        """
        try:
            partner = request.env['res.partner'].browse(partner_id)
            if not partner.exists():
                return request.make_response(
                    json.dumps(error_response(None, f"Partner with ID {partner_id} not found")),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            geolocation_data = {
                'partner_id': partner.id,
                'partner_name': partner.name,
                'latitude': partner.partner_latitude or 0.0,
                'longitude': partner.partner_longitude or 0.0,
                'accuracy_distance': partner.geolocation_accuracy_distance or 0.0,
                'has_geolocation': bool(partner.partner_latitude and partner.partner_longitude),
                'address': {
                    'street': partner.street or '',
                    'street2': partner.street2 or '',
                    'city': partner.city or '',
                    'state': partner.state_id.name if partner.state_id else '',
                    'zip': partner.zip or '',
                    'country': partner.country_id.name if partner.country_id else ''
                }
            }
            
            return request.make_response(
                json.dumps(success_response(geolocation_data, "Geolocation data retrieved successfully")),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.error(f"Error getting partner geolocation: {str(e)}")
            return request.make_response(
                json.dumps(error_response(e, "Failed to get partner geolocation")),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
