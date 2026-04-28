from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestTicket(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.infinito_from = "TEST COMPANY"
        cls.env.company.infinito_client_id = "client_id"
        cls.env.company.infinito_client_password = "client_password"

        cls.branch = cls.env['clinizone.branch'].create([{
            'name': 'Branch A',
            'company_id': cls.env.ref('base.main_company').id,
        }])

        cls.medical_team = cls.env['helpdesk.team'].create([{
            'name': 'Medical Team',
        }])

        cls.branch_team = cls.env['helpdesk.team'].create([{
            'name': 'Branch Team',
        }])

        cls.insurance_team = cls.env['helpdesk.team'].create([{
            'name': 'Insurance Team',
        }])

        cls.case_source_team = cls.env['helpdesk.team'].create([{
            'name': 'Case Source Team',
        }])

        cls.insurance_urgent_complaint_team = cls.env['helpdesk.team'].create([{
            'name': 'Insurance Urgent Complaint Team',
        }])

        cls.branch2 = cls.env['clinizone.branch'].create([{
            'name': 'Branch B',
            'company_id': cls.env.ref('base.main_company').id,
            'medical_director_team_id': cls.medical_team.id,
            'helpdesk_team_id': cls.branch_team.id,
        }])

        cls.case_source_1 = cls.env['clinizone.ram_case_source'].create([{
            'name': 'Case Source 1',
        }])

        cls.env['clinizone.ticket_team_assignment_rule'].create([{
            'name': 'Case Source Rule',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 1,
            'case_source_id': cls.case_source_1.id,
            'assignment_type': 'specific',
            'team_id': cls.case_source_team.id,
        }, {
            'name': 'Insurance Inquiry',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 10,
            'ticket_type_id': cls.env.ref('ramcrm.INSURANCE_INQUIRY').id,
            'branch_is_defined': False,
            'assignment_type': 'specific',
            'team_id': cls.insurance_team.id,
        }, {
            'name': 'Insurance Complaint',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 20,
            'ticket_type_id': cls.env.ref('ramcrm.INSURANCE_COMPLAINT').id,
            'branch_is_defined': False,
            'assignment_type': 'branch',
            'team_id': False,
        }, {
            'name': 'Insurance Inquiry',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 30,
            'ticket_type_id': cls.env.ref('ramcrm.INSURANCE_URGENT_COMPLAINT').id,
            'branch_is_defined': False,
            'assignment_type': 'specific',
            'team_id': cls.insurance_urgent_complaint_team.id,
        }, {
            'name': 'Medical Complaint',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 40,
            'ticket_type_id': cls.env.ref('ramcrm.MEDICAL_COMPLAINT').id,
            'branch_is_defined': False,
            'assignment_type': 'branch_medical_director',
            'team_id': False,
        }, {
            'name': 'Default (Branch not defined)',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 50,
            'ticket_type_id': False,
            'branch_is_defined': 'yes',
            'assignment_type': 'branch',
            'team_id': False,
        }, {
            'name': 'Default (Branch is defined)',
            'company_id': cls.env.ref('base.main_company').id,
            'sequence': 60,
            'ticket_type_id': False,
            'branch_is_defined': 'no',
            'assignment_type': 'specific',
            'team_id': cls.insurance_team.id,
        }])



    @patch('requests.post')
    def test_team_assignment(self, mocked_post):
        mocked_post.return_value.status_code = 200
        mocked_post.return_value.json = lambda: {'status': 'Success', 'statuscode': 200, 'statustext': 'OK'}
        with self.assertRaises(UserError) as e:
            t1 = self.env['helpdesk.ticket'].create({
                'ticket_type_id': self.env.ref('ramcrm.MEDICAL_COMPLAINT').id,
                'partner_phone': '0568303446',
            })
        self.assertEqual(str(e.exception), "Branch is not defined")

        with self.assertRaises(UserError) as e:
            t2 = self.env['helpdesk.ticket'].create({
                'ticket_type_id': self.env.ref('ramcrm.MEDICAL_COMPLAINT').id,
                'branch_id': self.branch.id,
                'partner_phone': '0568303446',
            })
        self.assertEqual(str(e.exception), "This branch does not have a medical director team")

        t3 = self.env['helpdesk.ticket'].create({
            'ticket_type_id': self.env.ref('ramcrm.MEDICAL_COMPLAINT').id,
            'branch_id': self.branch2.id,
            'partner_phone': '0568303446',
        })
        self.assertEqual(t3.team_id, self.medical_team)

        t4 = self.env['helpdesk.ticket'].create({
            'ticket_type_id': self.env.ref('ramcrm.INSURANCE_INQUIRY').id,
            'partner_phone': '0568303446',
        })
        self.assertEqual(t4.team_id, self.insurance_team)

        with self.assertRaises(UserError) as e:
            t5 = self.env['helpdesk.ticket'].create({
                'ticket_type_id': self.env.ref('ramcrm.INSURANCE_COMPLAINT').id,
            'partner_phone': '0568303446',
            })
        self.assertEqual(str(e.exception), "Branch is not defined")
        t5 = self.env['helpdesk.ticket'].create({
            'ticket_type_id': self.env.ref('ramcrm.INSURANCE_COMPLAINT').id,
            'branch_id': self.branch2.id,
            'partner_phone': '0568303446',
        })
        self.assertEqual(t5.team_id, self.branch2.helpdesk_team_id)

        t6 = self.env['helpdesk.ticket'].create({
            'ticket_type_id': self.env.ref('ramcrm.INSURANCE_URGENT_COMPLAINT').id,
            'partner_phone': '0568303446',
        })
        self.assertEqual(t6.team_id, self.insurance_urgent_complaint_team)

        t7 = self.env['helpdesk.ticket'].create({
            'ticket_type_id': self.env.ref('ramcrm.INQUIRY').id,
            'case_source_id': self.case_source_1.id,
            'partner_phone': '0568303446',
        })
        self.assertEqual(t7.team_id, self.case_source_team)

    @patch('requests.post')
    def test_sms(self, mocked_post):
        mocked_post.return_value.status_code = 200
        mocked_post.return_value.json = lambda: {'status': 'Success', 'statuscode': 200, 'statustext': 'OK'}
        t1 = self.env['helpdesk.ticket'].create({
            'ticket_type_id': self.env.ref('ramcrm.INSURANCE_INQUIRY').id,
            'branch_id': self.branch2.id,
            'partner_name': 'Partner Name',
            'partner_phone': '01000000000',
        })
        self.env.company.infinito_from = "Infinito"
        self.env.company.infinito_client_id = "client_id"
        self.env.company.infinito_client_password = "client_password"
        # TODO: with self.assertLogs(level='DEBUG') as logger_catcher:
        # TODO:    t1._send_ticket_created_sms()

        expected_sms_body = self.env.ref('ramcrm.sms_template_ticket_created')._render_field('body', [t1.id], compute_lang=True)[t1.id]
        expected_payload = {
            "apiver": "1.0",
            "sms": {
                "ver": "2.0",
                "dlr": {
                    "url": ""
                },
                "messages": [
                    {
                        "udh": "0",
                        "text": expected_sms_body,
                        "property": 0,
                        "id": "1",
                        "addresses": [
                            {
                                "from": "Infinito",
                                "to": '01000000000',
                                "seq": "1"
                            }
                        ]
                    }
                ]
            }
        }

        # TODO: self.assertIn(str(expected_payload), str(logger_catcher.output))