# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Bundle of Human Resource Employees Apps",
    'depends': [
                'hr_overtime_request',
                'hr_employee_orientation',
                'employee_travel_managment',
                'hr_employee_loan',
                'employee_advance_salary',
                'hr_employee_ideas',
                'employee_expense_advance',
                'hr_it_operations',
                'hr_visitor',
                'hr_exit_process',
                'hr_timesheet_status_report',
                #'odoo_hr_leave_extend',
                'odoo_hr_employee_shift',
                'employee_insurance_management',
                ],
    'price': 9.0,
    'version': '1.0',
    'currency': 'EUR',
    'category' : 'Human Resources/Employees',
    'license': 'Other proprietary',
    'summary': """This module contains bundle of HR Odoo Apps/Modules.""",
    'description': """
hr apps
    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/hrbun.jpg'],
    'data':[
        
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
