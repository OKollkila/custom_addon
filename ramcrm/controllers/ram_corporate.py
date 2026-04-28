from odoo import http, fields

class RamCorporate(http.Controller):
    @http.route('/api/ram_corporate', type='json', auth='api_key', cors='*', csrf=False)
    def ram_corporate(self):
        r = http.request.httprequest.json

        required_fields = [
            'name',
            'mobile',
            'company',
            'service',
            'city',
        ]
        for field in required_fields:
            if not r.get(field):
                return {
                    'success': False,
                    'msg': field + " is required"
                }

        source_id = False
        if r.get('source'):
            source = http.request.env['utm.source'].sudo().search([('name', '=', r.get('source'))], limit=1)
            if source:
                source_id = source.id

        lead = http.request.env['crm.lead'].sudo().create({
            'company_id': http.request.env.ref('ramcrm.company_RAM').id,
            'lead_source': 'Corporate',
            'lead_source_id': http.request.env.ref('ramcrm.lead_source_corporate').id,
            'source_id': source_id,
            'name': r.get('name'),
            'contact_name': r.get('name'),
            'phone': r.get('mobile'),
            'topic': r.get('service'),
            'city': r.get('city'),
            'notes': r.get('notes', ''),
            'campaign': r.get('company'),
            'user_id': False,
        })

        return {
            'success': True,
            'lead': lead.read(['id', 'name', 'phone', 'topic', 'city', 'notes', 'lead_source', 'campaign'])[0]
        }
