# -*- coding: utf-8 -*-

# from openerp import models, fields, api
from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta, MO,SU


class HrTimesheetStatusReportWizard(models.TransientModel):
    _name = 'hr.timesheet.status.report.wizard'
    _description = 'HrTimesheetStatusReportWizard'

    start_dt = fields.Datetime.from_string(fields.Datetime.now())
    monday = (start_dt + relativedelta(weekday=MO(-1))).replace(hour=0, minute=0, second=0)
    sunday = (start_dt + relativedelta(weekday=SU(+1))).replace(hour=23, minute=59, second=59)

    start_date = fields.Datetime(
        string = 'Start Date',
        required = True,
        default = monday,
    )
    end_date = fields.Datetime(
        string = 'End Date',
        required = True,
        default = sunday,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string = 'Employee',
        required = True,
    )
    
    # @api.multi #odoo13
    # def print_hr_timesheet_status_report(self, data):
    def print_hr_timesheet_status_report(self):
        # data.update({
        #     'employee_ids': self.employee_ids.ids,
        #     'start_date': self.start_date,
        #     'end_date': self.end_date,
        # })
        data = {
            'employee_ids': self.employee_ids.ids,
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return self.env.ref('hr_timesheet_status_report.action_report_hr_timesheet').report_action(self, data=data, config=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: