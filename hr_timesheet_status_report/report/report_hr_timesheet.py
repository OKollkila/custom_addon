# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
# from openerp import api, models, fields
from odoo import api, models, fields
from dateutil.relativedelta import relativedelta, MO,SU


class ReportHRTimesheet(models.AbstractModel):
    _name = 'report.hr_timesheet_status_report.report_hr_timesheet'
    _description = 'ReportHRTimesheet'
    
    def _get_hr_timesheet(self, date_print, monday, sunday, employees):
        data_dict = {}
        for employee in employees:
            timesheet_result = employee._get_hr_timesheet(date_print, monday, sunday, employees)
            if timesheet_result:
                if employee not in data_dict:
                    data_dict[employee] = {}
                    data_dict[employee]= timesheet_result
        return data_dict

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get("employee_ids",[]):
            employees = self.env['hr.employee'].search([('resource_calendar_id','!=', False)])
            date_print = fields.Datetime.from_string(fields.Datetime.now())
            monday = (date_print + relativedelta(weekday=MO(-1))).replace(hour=0, minute=0, second=0)
            sunday = (date_print + relativedelta(weekday=SU(+1))).replace(hour=23, minute=59, second=59)
            docs = self.env['hr.employee'].browse(docids)
            start_date = monday
            end_date = sunday
        else:
            employees_ids = data.get('employee_ids')
            employees = self.env['hr.employee'].browse(employees_ids)
            date_print = datetime.strptime(str(data.get('end_date')), '%Y-%m-%d %H:%M:%S')
            monday = (date_print + relativedelta(weekday=MO(-1))).replace(hour=0, minute=0, second=0)
            sunday = (date_print + relativedelta(weekday=SU(+1))).replace(hour=23, minute=59, second=59)
            docs = self.env['hr.employee'].browse(data.get('employee_ids')[0])
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d %H:%M:%S')
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d %H:%M:%S')
        get_hr_timesheet = self._get_hr_timesheet(date_print, monday, sunday, employees)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.employee',
            'docs': docs,
            'get_hr_timesheet': get_hr_timesheet,
            'start_time': start_date.date(),
            'end_time': end_date.date(),
        }
