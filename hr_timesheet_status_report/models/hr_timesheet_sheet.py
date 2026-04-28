# -*- coding: utf-8 -*-

# from openerp import api, fields, models, _
from odoo import api, fields, models, _


class AccountAnalyticLine(models.Model):
     _inherit = "account.analytic.line"

     @api.model
     def send_auto_reminder_unfilled_timesheet(self):
        user_id = self.env.user

        mail_template = False
        try:
            mail_template = self.env.ref('hr_timesheet_status_report.timesheet_status_mail_template')
        except:
            mail_template = False
        if not mail_template:
            return True

        ctx = self._context.copy()
        if user_id.company_id.pending_follower_ids:
            email = False
            emp = False
            for employee in user_id.company_id.pending_follower_ids:
                if employee.work_email:
                    if not email:
                        email = employee.work_email
                    else:
                        email = email + ',' + employee.work_email
                if not emp:
                    emp = employee


            if email and emp:
                ctx.update({
                    'email_from': user_id.company_id.email,
                    'email': email,
                })
                mail_template.with_context(ctx).send_mail(emp.id)


class hr_employee(models.Model):
    _inherit = 'hr.employee'
    
    @api.model
    def _get_hr_timesheet(self, date_print, monday, sunday, employees):
        timesheet_status = {}

        timesheet_obj = self.env['account.analytic.line']
        # check for if timesheet for employee for current week not created then return
        timesheets = timesheet_obj.search([('employee_id','=',self.id),
                                           ('date','>=',monday),
                                           ('date','<=',date_print)])
        if self.resource_calendar_id:
            consumed_hours = self.resource_calendar_id.get_work_hours_count(
                monday,
                sunday,
                compute_leaves=True)
            resource_id=self.resource_id.id
            consumed_hours = consumed_hours or 0.0
            total_hours = sum([i.unit_amount for i in timesheets])
            if total_hours < consumed_hours:
                timesheet_status.update({
                    'consumed_hours': consumed_hours,
                    'missing_hours': consumed_hours - total_hours,
                    'working_hour': total_hours,
                })
                return timesheet_status

        return timesheet_status
