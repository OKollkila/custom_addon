# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class hr_employee(models.Model):
    _inherit = 'hr.employee'
    
    custom_emp_overtime_ids = fields.One2many('hr.overtime', 'employee_id', string='Overtimes')
    
   # def get_overtime_hours(self, emp_id, date_from, date_to=None):
   #     if date_to is None:
   #         date_to = datetime.now().strftime('%Y-%m-%d')
   #     self._cr.execute("SELECT sum(o.number_of_hours) from hr_overtime as o where \
   #                         o.include_payroll IS TRUE and o.employee_id=%s \
   #                         and o.state='validate' AND o.date_from >= %s AND o.date_to <= %s ",
   #                         (emp_id, date_from, date_to))
   #     res = self._cr.fetchone()
   #     return res and res[0] or 0.0

