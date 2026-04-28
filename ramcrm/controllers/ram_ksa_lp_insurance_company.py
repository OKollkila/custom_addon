from odoo import http

from odoo.addons.ramcrm.controllers.utils import find_matching_lead_source, validate_service_id


class RamKsaLpInsuranceCompany(http.Controller):
    @http.route('/api/ram_ksa_lp_insurance_company', type='json', auth='api_key', cors='*', csrf=False)
    def ram_ksa_lp_insurance_company(self):
        r = http.request.httprequest.json

        #     Link_Page EX=> https://ram.medical-clinics.net/Insurance-companies
        #     Link_Page2 EX=> https://ram.medical-clinics.net/Insurance-for-all
        # RamLP_InsuranceCompany_Form

        required_fields = [
            # 'Ads', # string Of document_name
            'Lead_Name', # string Of Name
            'Topic', # Offer_Name && Offer_Price
            'MobileNumber', # string Of Number
            'Campaign', # string Of Page_Name
            # 'City', # string Of City_Name
            # 'CampaignActivity', # string Of insurance_name
            # 'Ad_Set', # string Of service_name,
            # 'patientId', # national_ID
            'Lead_Source', # LP Or Facebook , Instagram , Snapchat
            # 'timestamp', # Request created_at" Format('Y-m-d H:i:s') EX: 2023-06-10 16:48:01
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

        lead = http.request.env['crm.lead'].sudo().create({
            'company_id': http.request.env.ref('ramcrm.company_RAM').id,
            'ads': r.get('Ads'),
            'ad_set': r.get('Ad_Set'),
            'source_id': http.request.env.ref('ramcrm.lp_insurance_company').id,
            'name': r.get('Lead_Name'),
            'contact_name': r.get('Lead_Name'),
            'phone': r.get('MobileNumber'),
            'topic': r.get('Topic'),
            'campaign': r.get('Campaign'),
            'campaign_activity': r.get('CampaignActivity'),
            'patient_id': r.get('PatientId', r.get('patientId')),
            'city': r.get('City'),
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
