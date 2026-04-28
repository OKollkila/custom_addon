# -*- coding: utf-8 -*-
import io
import json
from datetime import date

from odoo import models
from odoo.tools import json_default
from odoo.fields import Datetime

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class EmployeeAttendanceXlsx(models.AbstractModel):
    _name = 'report.employee_attendance_xlsx'
    _description = 'Employee Attendance XLSX Report'

    # ---------------------------------------------------------
    # ACTION CALLED FROM SERVER ACTION
    # ---------------------------------------------------------
    def action_print_xlsx(self, attendance_ids=None):
        if attendance_ids is None:
            attendance_ids = self.env.context.get('active_ids', [])
        if not attendance_ids:
            return False

        data = {
            'attendance_ids': attendance_ids,
            'from_date': date.today(),
            'to_date': date.today(),
        }

        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'report.employee_attendance_xlsx',
                'options': json.dumps(data, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Attendance Report',
            },
            'report_type': 'xlsx',
        }

    # ---------------------------------------------------------
    # XLSX CONTENT
    # ---------------------------------------------------------
    def get_xlsx_report(self, data, response):

        query = """
            SELECT 
                hr_e.barcode AS badge_number,
                hr_e.name AS employee,
                hr_at.check_in,
                hr_at.check_out,
                hr_at.worked_hours
            FROM hr_attendance hr_at
            LEFT JOIN hr_employee hr_e ON hr_at.employee_id = hr_e.id
            WHERE hr_at.id IN %s
        """

        self.env.cr.execute(query, (tuple(data['attendance_ids']),))
        docs = self.env.cr.dictfetchall()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Attendance Report')

        header = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center'
        })
        cell = workbook.add_format({
            'border': 1,
            'align': 'center'
        })

        headers = [
            'Code',
            'Employee',
            'Check In Date',
            'Check Out Date',
            'Check In Time',
            'Check Out Time',
            'Worked Hours',
            'Over Time'
        ]

        for col, h in enumerate(headers):
            sheet.set_column(col, col, 18)
            sheet.write(0, col, h, header)

        row = 1
        standard_hours = 8

        for rec in docs:

            check_in = rec['check_in']
            check_out = rec['check_out']
            worked_hours = rec['worked_hours'] or 0.0

            if check_in:
                check_in = Datetime.context_timestamp(self.env.user, check_in)
            if check_out:
                check_out = Datetime.context_timestamp(self.env.user, check_out)

            overtime = worked_hours - standard_hours if worked_hours > standard_hours else 0.0

            sheet.write(row, 0, rec['badge_number'] or '', cell)
            sheet.write(row, 1, rec['employee'] or '', cell)

            sheet.write(row, 2, str(check_in.date()) if check_in else '', cell)
            sheet.write(row, 3, str(check_out.date()) if check_out else '', cell)

            sheet.write(row, 4, check_in.strftime('%H:%M') if check_in else '', cell)
            sheet.write(row, 5, check_out.strftime('%H:%M') if check_out else '', cell)

            sheet.write(row, 6, round(worked_hours, 2), cell)
            sheet.write(row, 7, round(overtime, 2), cell)

            row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
