import datetime
import json
import logging
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, HttpCase

_logger = logging.getLogger()

class Checkout(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env['res.users'].create({'name': 'User 1', 'login': 'user1'})
        cls.user.write({'groups_id': [(4, cls.env.ref('cz_reviews.group_checkout_api').id)]})
        cls.api_key = cls.env['res.users.apikeys'].with_user(cls.user)._generate(None, 'API Key', datetime.datetime.now() + datetime.timedelta(days=90))
        _logger.info(f"API Key: {cls.api_key}")
        cls.branch = cls.env['clinizone.branch'].create({'name': 'Branch 1', 'code': 'B1', 'prime_care_code': 'BPC1', 'company_id': cls.env.company.id})
        cls.department = cls.env['clinizone.department'].create({'name': 'Department 1', 'prime_care_code': 'DPC1'})
        cls.env.company.checkout_review_template = 'survey_test'
        cls.env.company.checkout_survey_id = cls.env['survey.survey'].create({'title': 'Survey Test'}).id

    @patch('requests.post')
    def no_test_checkout_01(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
          "message": "Message successfully queued.",
          "messageId": "SOME_MESSAGE_ID",
          "applicationId": "SOME_APPLICATION_ID",
        }
        response = self.url_open(f"/api/prime_care/checkout/", headers={'Authorization': self.api_key, 'Content-Type': 'application/json'},
            data=json.dumps({
                'mrno': '123456',
                'patient_name': 'Patient 1',
                'mobile_number': '+201003535886',
                'department': 'DPC1',
                'branch': 'BPC1',
                'doctor_name': 'Dr. A',
                'machine_name': 'Machine 1',
                'technician_name': 'Technician 1',
                'payment_type_string': 'cash',
            })); self.assertEqual(response.status_code, 200)
        ret = response.json()
        _logger.info(ret['result'])
        self.assertEqual(ret['result']['success'], True)
        self.assertEqual(ret['result']['data']['mrno'], '123456')
        self.assertEqual(ret['result']['data']['patient_name'], 'Patient 1')
        self.assertEqual(ret['result']['data']['mobile_number'], '+201003535886')
        self.assertEqual(ret['result']['data']['department_id'], [self.department.id, 'Department 1'])
        self.assertEqual(ret['result']['data']['branch_id'], [self.branch.id, 'Branch 1'])
        self.assertEqual(ret['result']['data']['doctor_name'], 'Dr. A')
        self.assertEqual(ret['result']['data']['machine_name'], 'Machine 1')
        self.assertEqual(ret['result']['data']['technician_name'], 'Technician 1')
        self.assertEqual(ret['result']['data']['payment_type_string'], 'cash')

        checkout = self.env['clinizone.checkout'].browse(ret['result']['data']['id'])
        checkout.old_create_user_input()
        checkout.old_send_review_message_with_url_to_odoo_survey()
        self.assertIsNot(checkout.review_message_sent_date_whatsapp, False)
        user_input = self.env['survey.user_input'].search([('checkout_id', '=', checkout.id)], limit=1)
        self.assertTrue(user_input.checkout_id.id > 0)
        _logger.info(f"Survey URL: {user_input.absolute_url}")

    @patch('requests.post')
    def test_send_whatsapp(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
          "message": "Message successfully queued.",
          "messageId": "SOME_MESSAGE_ID",
          "applicationId": "SOME_APPLICATION_ID",
        }
        checkout = self.env['clinizone.checkout'].create({
            'mrno': '123456',
            'patient_name': 'Patient 1',
            'mobile_number': '+201003535886',
            'department': 'DPC1',
            'branch': 'BPC1',
            'doctor_name': 'Dr. A',
            'machine_name': 'Machine 1',
            'technician_name': 'Technician 1',
            'payment_type_string': 'cash',
        })
        checkout.send_unifonic_whatsapp_message()
        self.assertTrue(checkout.review_message_sent_date_whatsapp != False)

    @patch('requests.post')
    def test_poll_01(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
          "id": "111477935",
          "firstName": "Clinizone",
          "userName": "clinizone",
          "email": "Pmo@clinizone.net",
          "mobile": "000000000",
          "token": "TOKEN",
          "branch": "Ram Alaqrabiah",
          "department": "Call Center",
          "designation": "Sales representative",
          "clientId": "111477932",
          "clientPages": [],
          "profileImg": [
          ],
          "roles": [],
          "permissions": [],
          "menuAccess": [],
          "adminPages": [],
          "companyCode": "TECHNAS",
          "divisionCode": "CHN",
          "allowedDivisions": [
            "CHN"
          ]
        }
        poll = self.env['cz.prime_care_checkout_poll'].create([{
            'date': fields.Date.today(),
        }])
        self.env.company.prime_care_token = False
        self.env.company.prime_care_login_url = 'http://example.com'
        self.env.company.prime_care_username = 'user'
        self.env.company.prime_care_password = 'pass'
        self.env['cz.prime_care_checkout_poll'].create_prime_care_token()
        self.assertNotEqual(self.env.company.prime_care_token, False)
        _logger.info(f"Token: {self.env.company.prime_care_token}")
        self.assertEqual(self.env.company.prime_care_company, 'TECHNAS')
        self.assertEqual(self.env.company.prime_care_division, 'CHN')

    @patch('requests.get')
    def test_poll_02(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
          [
            "MRNO",
            "PATIENT NAME",
            "MOBILE NUMBER",
            "DEPARTMENT",
            "BRANCH",
            "BRANCH NAME AR",
            "DR NAME ??",
            "",
            "",
            "DR NAME",
            "PAYMENT TYPE",
          ]
        ]

        self.env.company.prime_care_checkouts_url = 'http://example.com'
        self.env.company.prime_care_token = 'TOKEN'
        yesterday = fields.Date.today() - timedelta(days=1)
        cos = self.env['cz.prime_care_checkout_poll'].do_prime_care_poll(yesterday)
        self.assertTrue(len(cos) > 0)
        self.assertEqual(cos[0].mrno, 'MRNO')
        self.assertEqual(cos[0].patient_name, 'PATIENT NAME')
        self.assertEqual(cos[0].mobile_number, 'MOBILE NUMBER')
        self.assertEqual(cos[0].branch_ar , 'BRANCH NAME AR')
        self.assertEqual(cos[0].branch , 'BRANCH')
        self.assertEqual(cos[0].doctor_name, 'DR NAME')

        yesterday_poll = self.env['cz.prime_care_checkout_poll'].search([('date', '=', yesterday)], limit=1)
        self.assertTrue(yesterday_poll.state == 'done')
        _logger.info(f"Poll State: {yesterday_poll.state}")
