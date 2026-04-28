from datetime import datetime

from odoo import http

class WhatsAppChatbot(http.Controller):
    @http.route('/api/whatsapp-chatbot', type='json', auth='api_key', cors='*', csrf=False)
    def whatsapp_chatbot(self):
        r = http.request.httprequest.json
        required_fields = [
            'name',
            'phone',
            'city',
            'topic',
        ]

        for field in required_fields:
            if not r.get(field):
                return {
                    'success': False,
                    'msg': field + " is required"
                }

        lead = http.request.env['crm.lead'].sudo().create({
            'company_id': http.request.env.ref('ramcrm.company_RAM').id,
            'branch_id': r.get('branch_id'),
            'source_id': http.request.env.ref('ramcrm.UTM_SOURCE_WHATSAPP_CHATBOT').id,
            'name': r.get('name'),
            'contact_name': r.get('Lead_Name'),
            'phone': r.get('phone'),
            'topic': r.get('topic'),
            'campaign': '???',
            'city': r.get('city'),
            'lead_source_id': http.request.env.ref('ramcrm.lead_source_whatsapp_chatbot').id,
            'timestamp': datetime.now(),
            'user_id': False,
        })

        return {
            'success': True,
            'lead': lead.to_json()
        }
