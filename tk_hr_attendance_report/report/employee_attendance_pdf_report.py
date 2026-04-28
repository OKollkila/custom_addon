# -*- coding: utf-8 -*-
from datetime import datetime, time
from odoo import models, api


class EmployeeAttendancePdfReport(models.AbstractModel):
    """
    This class is responsible for generating the employee report in PDF format.
    It uses a template to render the report.
    """
    _name = 'report.tk_hr_attendance_report.emp_attendance_report_template'
    _description = 'Employee PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        form_data = data.get('form_data')
        employee_id = form_data.get('employee_id')

        employees = self.env['hr.employee'].search([])

        if employee_id:
            employees = self.env['hr.employee'].browse(employee_id[0])

        employee_data_list = []

        start_date = datetime.strptime(form_data.get('start_date'), "%Y-%m-%d").date()
        end_date = datetime.strptime(form_data.get('end_date'), "%Y-%m-%d").date()

        start_date_dt = datetime.combine(start_date, time.min)
        end_date_dt = datetime.combine(end_date, time.max)

        for employee in employees:
            attendance_domain = [
                ('employee_id', '=', employee.id),
                ('check_in', '<=', end_date_dt),
                ('check_out', '>=', start_date_dt),
            ]
            leave_domain = [
                ('employee_id', '=', employee.id),
                ('request_date_from', '<=', end_date_dt),
                ('request_date_to', '>=', start_date_dt),
                ('state', '=', 'validate'),
            ]
            attendances = self.env['hr.attendance'].search(attendance_domain)
            leaves = self.env['hr.leave'].search(leave_domain)

            attendance_data = []
            total_worked_hours = 0.0
            total_duration_str = ' '

            for attendance_move in attendances:
                worked_hours = attendance_move.worked_hours
                total_worked_hours += worked_hours

                hours = int(worked_hours)
                minutes = int(round((worked_hours - hours) * 60))
                worked_hours_str = f"{hours} Hours {minutes} Minutes"

                attendance_data.append({
                    'check_in': attendance_move.check_in,
                    'check_out': attendance_move.check_out,
                    'worked_hours': worked_hours_str,
                })

                total_hours = int(total_worked_hours)
                total_minutes = int(round((total_worked_hours - total_hours) * 60))
                total_duration_str = f"{total_hours} Hours {total_minutes} Minutes"

            leaves_data = []
            for leave_move in leaves:
                leaves_data.append({
                    'holiday_status_id': leave_move.holiday_status_id.name,
                    'request_date_to': leave_move.request_date_to,
                    'request_date_from': leave_move.request_date_from,
                    'name': leave_move.name or '',
                })

            employee_data_list.append({
                'employee_name': employee.name,
                'attendance_data': attendance_data,
                'leaves_data': leaves_data,
                'total_duration_str': total_duration_str,
            })

        return {
            'employee_data_list': employee_data_list,
            'from_date': start_date,
            'to_date': end_date,
        }
