# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class EmployeeAttendanceReport(models.TransientModel):
    """
        Inherits from 'hr.employee' to customize behavior or add additional fields.
    """
    _name = 'employee.attendance.report'
    _description = 'Employee Attendance Report'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    start_date = fields.Date(string="From Date", required=True)
    end_date = fields.Date(string="To Date", required=True)

    def employee_pdf_report(self):
        """
        Generates the employee attendance report in PDF format based on the
        provided date range and filters.
        """
        self.ensure_one()
        if self.start_date > self.end_date:
            raise UserError(_("The start date cannot be after the end date."))
        data = {
            'form_data': self.read()[0],

        }
        return (self.env.ref('tk_hr_attendance_report.employee_attendance_report_action')
                .report_action(self, data=data))
