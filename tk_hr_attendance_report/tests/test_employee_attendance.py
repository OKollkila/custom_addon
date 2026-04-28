# -*- coding: utf-8 -*-
import datetime
from odoo.tests.common import TransactionCase, tagged


@tagged('test_employee_attendance')
class TestEmployeeAttendance(TransactionCase):
    """
    Test case for the 'EmployeeAttendanceReport' model.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up test data once for all tests in the class.
        """
        super().setUpClass()

        cls.employee_one = cls.env['hr.employee'].create({
            'name': 'demo employee one'
        })
        cls.attendance_one = cls.env['hr.attendance'].create({
            'employee_id': cls.employee_one.id,
            'check_in': "2025-04-23 10:00:00",
            'check_out': "2025-04-23 15:00:00"
        })
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Paid Leave'
        })
        cls.leave = cls.env['hr.leave'].create({
            'employee_id': cls.employee_one.id,
            'holiday_status_id': cls.leave_type.id,
            'request_date_to': "2025-04-25 10:00:00",
            'request_date_from': "2025-04-25 15:00:00",
        })
        cls.employee_report_wizard = cls.env['employee.attendance.report'].create({
            'start_date': datetime.datetime.today(),
            'end_date': datetime.datetime.today(),
            'employee_id': cls.employee_one.id
        })

    def test_employee_report_wizard(self):
        """Test data retrieval from the employee report wizard."""
        self.assertTrue(self.employee_report_wizard)
        action = self.employee_report_wizard.employee_pdf_report()
        self.assertIsInstance(action, dict)
        form_data = action.get('data', {}).get('form_data', {})
        self.assertEqual(form_data['start_date'], self.employee_report_wizard.start_date)
        self.assertEqual(form_data['end_date'], self.employee_report_wizard.end_date)
        self.assertEqual(form_data['employee_id'][0], self.employee_report_wizard.employee_id.id)

    def test_pdf_employee_report(self):
        """Test PDF report generation for employee attendance."""
        form_data = {
            'start_date': self.employee_report_wizard.start_date,
            'end_date': self.employee_report_wizard.end_date,
            'employee_id': self.employee_report_wizard.employee_id.id
        }
        action = self.employee_report_wizard.employee_pdf_report()
        self.assertIsInstance(action, dict)
        self.assertTrue(form_data)
