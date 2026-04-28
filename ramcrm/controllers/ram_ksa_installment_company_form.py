from odoo import http

from odoo.addons.ramcrm.controllers.utils import find_matching_lead_source, validate_service_id


class RamKsaInstallmentCompanyForm(http.Controller):
    @http.route('/api/ram_ksa_installment_company_form', type='json', auth='api_key', cors='*', csrf=False)
    def ram_ksa_installment_company_form(self):
        r = http.request.httprequest.json

        # https://ramclinics.net/page/installment
        # RamKsa_installment_company_formV2.json

        required_fields = [
            # 'Ad_Set', # installment company
            # 'BU', # Branch_Code
            'Lead_Name', # string Of Name
            'MobileNumber', # string Of Number
            # 'Email', # Lead_Mail
            'Topic', # Offer_Name && Offer_Price
            # 'treatingdoctor', # Dr_Name
            # 'City', # string Of City_Name
            # 'Speciality', # Specialty_Name
            'Campaign', # Doctor Dental , Doctor Derma , Doctor Medical
            # 'Installment', # string Of Installment Company name Tamweel-Aloula Or Tashel
            'Lead_Source', # Website Or Facebook , Instagram , Snapchat
            # 'patientId', # String Of national_ID
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
            'company_id': http.request.env.ref('ramcrm.company_RAM').id,
            'branch_id': branch_id.id,
            'bu': r.get('BU'),
            'installment_company': r.get('Ad_Set'),
            'source_id': http.request.env.ref('ramcrm.installment_company_form').id,
            'name': r.get('Lead_Name'),
            'contact_name': r.get('Lead_Name'),
            'phone': r.get('MobileNumber'),
            'email_from': r.get('Email'),
            'topic': r.get('Topic'),
            'treating_doctor': r.get('treatingdoctor'),
            'city': r.get('City'),
            'speciality': r.get('Speciality'),
            'campaign': r.get('Campaign'),
            'installment': r.get('Installment'),
            'lead_source': lead_source,
            'lead_source_id': lead_source_id.id,
            'patient_id': r.get('patientId'),
            'timestamp': r.get('timestamp'),
            'user_id': False,
            'service_id': service.id if service else False,
            'department_id': service.department_id.id if service else False,
        })

        return {
            'success': True,
            'lead': lead.to_json()
        }
