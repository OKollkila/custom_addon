# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

{
    'name':'Employee Insurance Management',
    'version':'1.0',
    'price': 79.0,
    'category': 'Human Resources',
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': 'This app allow you to manage Insurance of your Employees.',
    'description': """
Employees
Employee Insurance
Health Insurance
Insurance odoo
Insurance Management Systems
Insurance providers
Insurance provider
Insurance
user Insurance
    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/employee_insurance_management/826',#'https://youtu.be/890a5218kAA',
    'depends': [
        'hr',
    ],
    'data':[
        'data/employee_insurance_policy_expire.xml',
        'data/employee_insurance_policy_reminder.xml',
        'security/insurance_security.xml',
        'security/ir.model.access.csv',
        'wizard/policy_renew.xml',
        'views/employee_insurance.xml',
        'views/insurance_property.xml',
        'views/employee_view.xml',
        'views/res_config_settings_view.xml',
        'report/insurance.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
