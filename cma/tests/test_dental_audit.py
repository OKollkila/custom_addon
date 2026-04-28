from datetime import timedelta, datetime, date

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDentalAudit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.branch = cls.env['clinizone.branch'].create({
            'name': 'Branch A',
            'company_id': cls.env.ref('base.main_company').id,
        })
        cls.prime_care_branch = cls.env['clinizone.prime_care_branch'].create({
            'name': 'Prime Care Branch A',
            'branch_id': cls.branch.id,
        })

    def test_no_duplicates_within_3_days(self):
        some_datetime = datetime(2024, 11, 1, 10, 0, 0)
        with patch.object(self.env.cr, 'now', return_value=some_datetime):
            r1 = self.env['clinizone.dental_audit'].create({
                'prime_care_branch_id': self.prime_care_branch.id,
                'mobile': '0555555555',
                'treatment_doctor': 'Dr. A',
                'mdr': '123',
                'patient_name': 'Patient A',
                'clinic': 'Clinic A',
            })
            self.assertEqual(r1.create_date, some_datetime)

        some_date_plus_4 = some_datetime + timedelta(days=4)
        with patch.object(self.env.cr, 'now', return_value=some_date_plus_4):
            r2 = self.env['clinizone.dental_audit'].create({
                'prime_care_branch_id': self.prime_care_branch.id,
                'mobile': '0555555555',
                'treatment_doctor': 'Dr. A',
                'mdr': '123',
                'patient_name': 'Patient A',
                'clinic': 'Clinic A',
            })
            self.assertEqual(r2.create_date, some_date_plus_4)

        some_date_plus_2 = some_datetime + timedelta(days=2)
        with patch.object(self.env.cr, 'now', return_value=some_date_plus_2):
            with self.assertRaises(ValidationError):
                self.env['clinizone.dental_audit'].create({
                    'prime_care_branch_id': self.prime_care_branch.id,
                    'mobile': '0555555555',
                    'treatment_doctor': 'Dr. A',
                    'mdr': '123',
                    'patient_name': 'Patient A',
                    'clinic': 'Clinic A',
                })
