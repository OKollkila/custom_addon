from odoo import http

from odoo.addons.ramcrm.controllers.utils import find_matching_lead_source, validate_service_id


class DohaOnlineForm(http.Controller):
    @http.route('/api/doha_online_form', type='json', auth='api_key', cors='*', csrf=False)
    def doha_online_form(self):
        r = http.request.httprequest.json

        # https://dohaclinics.sa/offers
        # DohaLP_insuranceCompany_Form.json

        required_fields = [
            # 'BU', # Doha Medical Center
            'Lead_Name', # string Of Name
            'Topic', # Offer_Name && Offer_Price
            'MobileNumber', # string Of Number
            # 'Email', # Lead_Mail
            # 'City', # Doha
            'Campaign', # string Of Campaign Name", EX: Eid Fetr 2024
            # 'Notes', # Payment_Type && Payment_Status
            'Lead_Source', # Lead_Source Online Or Facebook, Instagram, Snapchat
            # 'timestamp' # Request created_at" Format('Y-m-d H:i:s') EX: 2023-06-10 16:48:01
        ]
        for field in required_fields:
            if not r.get(field):
                return {
                    'success': False,
                    'msg': field + " is required"
                }

        lead_source = r.get('Lead_Source')
        lead_source_id = find_matching_lead_source(http.request.env, lead_source)
        if not lead_source_id:
            return {
                'success': False,
                'msg': "Lead_Source is invalid"
            }

        service = validate_service_id(http.request.env, r.get('service_id'))

        branch_code = r.get('BU')
        branch_id = http.request.env['clinizone.branch'].search([('code', '=', branch_code)], limit=1)
        lead = http.request.env['crm.lead'].sudo().create({
            'company_id': http.request.env.ref('ramcrm.company_DOHA').id,
            'branch_id': branch_id.id,
            'bu': r.get('BU'),
            'source_id': http.request.env.ref('ramcrm.doha_online_form').id,
            'name': r.get('Lead_Name'),
            'contact_name': r.get('Lead_Name'),
            'phone': r.get('MobileNumber'),
            'email_from': r.get('Email'),
            'topic': r.get('Topic'),
            'city': r.get('City'),
            'campaign': r.get('Campaign'),
            'notes': r.get('Notes'),
            'lead_source': lead_source,
            'lead_source_id': lead_source_id.id,
            'timestamp': r.get('timestamp'),
            'user_id': False,
            'service_id': service.id if service else False,
            'department_id': service.department_id.id if service else False,
        })

        return {
            'success': True,
            'lead': lead.to_json()
        }
