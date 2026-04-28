from datetime import datetime

from odoo import http

class WhatsAppCheckout(http.Controller):
    @http.route('/api/whatsapp-checkout-bad-survey', type='json', auth='api_key', cors='*', csrf=False)
    def whatsapp_checkout_survey_bad(self):
        r = http.request.httprequest.json
        required_fields = [
            'checkout_id',
            'survey_result',
        ]

        for field in required_fields:
            if not r.get(field):
                return {
                    'success': False,
                    'msg': field + " is required"
                }

        checkout_id_id = int(r.get('checkout_id'))
        checkout = http.request.env['clinizone.checkout'].sudo().browse(checkout_id_id)
        if not checkout:
            return {
                'success': False,
                'msg': 'Checkout not found'
            }

        lead = http.request.env['crm.lead'].sudo().create({
            'company_id': checkout.branch_id.company_id.id,
            'branch_id': checkout.branch_id.id,
            'department_id': checkout.department_id.id,
            'treating_doctor': checkout.doctor_name,
            'source_id': http.request.env.ref('ramcrm.UTM_SOURCE_WHATSAPP_CHECKOUT_SURVEY_BAD').id,
            'name': checkout.patient_name,
            'contact_name': checkout.patient_name,
            'phone': checkout.mobile_number,
            'patient_id': checkout.mrno,
            'topic': r.get('survey_result'),
            'campaign': '???',
            'city': checkout.branch_id.city_id.name,
            'lead_source_id': http.request.env.ref('ramcrm.lead_source_whatsapp_checkout_survey_bad').id,
            'timestamp': datetime.now(),
            'user_id': False,
        })

        return {
            'success': True,
            'lead': lead.to_json()
        }
