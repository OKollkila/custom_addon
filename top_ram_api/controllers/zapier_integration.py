from odoo import http
from odoo.addons.ramcrm.controllers.utils import find_matching_lead_source

class ZapierIntegration(http.Controller):
    @http.route('/api/zapier_v2', type='json', auth='api_key', cors='*', csrf=False)
    def handle_zapier_request(self):
        # ملحوظة: لو اشتغل معاكي بـ httprequest.json سيبيه كما هو،
        # ولو رجع جاب "name is required" غيريه لـ http.request.params
        r = http.request.httprequest.json

        required_fields = [
            'name',
            'phone_number',
            'lead_source',
            'campaign',
            'topic',
            'city',  # إضافة المدينة كحقل إجباري
        ]

        # التحقق من وجود الحقول
        for field in required_fields:
            if not r.get(field):
                return {
                    'success': False,
                    'msg': f"{field} is required"
                }

        lead_source = r.get('lead_source')
        lead_source_id = find_matching_lead_source(http.request.env, lead_source)

        if not lead_source_id:
            return {
                'success': False,
                'msg': "Lead Source is invalid"
            }

        # إنشاء الـ Lead
        lead = http.request.env['crm.lead'].sudo().create({
            'company_id': r.get('company_id'),
            'branch_id': r.get('branch_id'),
            'name': r.get('name'),
            'contact_name': r.get('name'),
            'phone': r.get('phone_number'),
            'email_from': r.get('email'),
            'topic': r.get('topic'),
            'city': r.get('city'),
            'campaign': r.get('campaign'),
            'source_id': http.request.env.ref('ramcrm.UTM_SOURCE_ZAPIER').id,
            'lead_source': lead_source,
            'lead_source_id': lead_source_id.id,
            'user_id': False,
        })

        # إرجاع بيانات السجل
        return {
            'success': True,
            'lead': lead.read(
                ['id', 'name', 'phone', 'email_from', 'topic', 'campaign', 'lead_source', 'lead_source_id', 'city_id'])
        }