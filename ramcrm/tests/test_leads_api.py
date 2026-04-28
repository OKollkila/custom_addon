import datetime
import json
import logging

from odoo.tests.common import HttpCase

_logger = logging.getLogger()

class LeadsApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env['res.users'].create({'name': 'User 1', 'login': 'user1'})
        cls.user.write({'groups_id': [(4, cls.env.ref('sales_team.group_sale_salesman').id)]})
        cls.api_key = cls.env['res.users.apikeys'].with_user(cls.user)._generate(None, 'API Key', datetime.datetime.now() + datetime.timedelta(days=90))
        _logger.info(f"API Key: {cls.api_key}")
        cls.city = cls.env['clinizone.city'].create({'name': 'City 1', 'code': 'C1'})
        cls.branch = cls.env['clinizone.branch'].create({'name': 'Branch 1', 'code': 'B1', 'company_id': cls.env.company.id, 'city_id': cls.city.id})
        cls.department = cls.env['clinizone.department'].create({'name': 'Department 1'})
        cls.service = cls.env['clinizone.service'].create({'name': 'Service 1', 'department_id': cls.department.id})
        cls.lead_source = cls.env['clinizone.lead_source'].create({'name': 'Lead Source 1'})
        cls.data = {
                'Lead_Name': '<NAME>',
                'MobileNumber': '<NUMBER>',
                'Topic': '<TOPIC>',
                'Campaign': '<CAMPAIGN>',
                'Lead_Source': cls.lead_source.name,
                'BU': cls.branch.code,
                'City': cls.city.name,
                'Email': '<EMAIL>',
                'treatingdoctor': '<DOCTOR>',
                'Speciality': '<SPECIALITY>',
                'Notes': '<Notes>',
                'service_id': cls.service.id,
            }
        cls.headers = {'Authorization': cls.api_key, 'Content-Type': 'application/json'}

    def validate_lead(self, response):
        self.assertEqual(response.status_code, 200)
        ret = response.json()
        self.assertEqual(ret['result']['success'], True)
        lead = self.env['crm.lead'].browse(ret['result']['lead']['id'])
        self.assertTrue(lead.id > 0)
        return lead

    def test_doha_dt_form(self):
        lead = self.validate_lead(self.url_open('/api/doha_dr_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_DOHA').id)
        self.assertEqual(lead.branch_id.id, self.branch.id)
        self.assertEqual(lead.source_id.id, self.env.ref('ramcrm.doha_dr_form').id)
        self.assertEqual(lead.name, '<NAME>')
        self.assertEqual(lead.contact_name, '<NAME>')
        self.assertEqual(lead.phone, '<NUMBER>')
        self.assertEqual(lead.email_from, '<EMAIL>')
        self.assertEqual(lead.topic, '<TOPIC>')
        self.assertEqual(lead.treating_doctor, '<DOCTOR>')
        self.assertEqual(lead.speciality, '<SPECIALITY>')
        self.assertEqual(lead.campaign, '<CAMPAIGN>')
        self.assertEqual(lead.notes, '<Notes>')
        self.assertEqual(lead.name, '<NAME>')
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

    def test_company(self):
        lead = self.validate_lead(self.url_open('/api/doha_dr_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_DOHA').id)
        lead = self.validate_lead(self.url_open('/api/doha_installment_company_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_DOHA').id)
        lead = self.validate_lead(self.url_open('/api/doha_lp', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_DOHA').id)
        lead = self.validate_lead(self.url_open('/api/doha_lp_insurance_company_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_DOHA').id)
        lead = self.validate_lead(self.url_open('/api/doha_online_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_DOHA').id)
        lead = self.validate_lead(self.url_open('/api/ram_ksa_dr_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_RAM').id)
        lead = self.validate_lead(self.url_open('/api/ram_ksa_installment_company_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_RAM').id)
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_dr', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_RAM').id)
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_offer', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_RAM').id)
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_insurance_company', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_RAM').id)
        lead = self.validate_lead(self.url_open('/api/ram_ksa_online_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.company_id.id, self.env.ref('ramcrm.company_RAM').id)

    def test_service(self):
        data_no_service_id = self.data.copy()
        del(data_no_service_id['service_id'])
        data_bad_service_id = self.data.copy()
        data_bad_service_id['service_id'] = 999999999

        self.validate_lead(self.url_open('/api/doha_dr_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        self.validate_lead(self.url_open('/api/doha_dr_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_dr_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/doha_installment_company_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_installment_company_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_installment_company_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/doha_lp', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_lp', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_lp', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/doha_lp_insurance_company_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_lp_insurance_company_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_lp_insurance_company_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/doha_online_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_online_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/doha_online_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/ram_ksa_dr_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_dr_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_dr_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/ram_ksa_installment_company_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_installment_company_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_installment_company_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_dr', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_dr', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_dr', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_offer', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_offer', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_for_offer', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_insurance_company', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_insurance_company', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_lp_insurance_company', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)

        lead = self.validate_lead(self.url_open('/api/ram_ksa_online_form', headers=self.headers, data=json.dumps(data_no_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_online_form', headers=self.headers, data=json.dumps(data_bad_service_id)))
        lead = self.validate_lead(self.url_open('/api/ram_ksa_online_form', headers=self.headers, data=json.dumps(self.data)))
        self.assertEqual(lead.service_id.id, self.service.id)
        self.assertEqual(lead.department_id.name, self.department.name)


