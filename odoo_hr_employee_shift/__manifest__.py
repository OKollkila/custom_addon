# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Employee Shift Management',
    'license': 'Other proprietary',
    'version': '1.0',
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'category' : 'Human Resources',
    'price': 99.0,
    'currency': 'EUR',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/odoo_hr_employee_shift/1002',#'https://youtu.be/1tKoL1JjMCY',
    'images': ['static/description/image.png'],
    'website': 'https://www.probuse.com',
    'summary': """This module do Shift Management section of Human Resources helps your company to manage shifts of your employees.""",
    'description': ''' 
This module add below features which can be used to manage Shift requests
Shifts/Requests
Shifts/Requests/My Shift Requests
Shifts/Requests/Shift Request to Approve
Shifts/Requests/All Shift Requests
Shifts/Configuration/Shift Types
employee shift
shift managment
hr shift
work shift
shift odoo
Shift Management
Shift Type
Shift Request
Shift Assignment
shift-management
  ''',
    'depends':['hr','portal'],
    'data' : [
              'data/sequence_shift.xml',
              'security/shift_security.xml',
              'security/ir.model.access.csv',
              'views/shift_type.xml',
              'views/hr_shift_request.xml',
              'views/hr_shift_request_employee.xml',
              'report/shift_type.xml',
              ],
    'installable':True,
    'auto_install':False

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
