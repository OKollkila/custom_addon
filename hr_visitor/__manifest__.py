# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.
{
    'name': "Human Resource - Company Visitors Pass",
    'version': '1.0',
    'price': 30.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Human Resources/Employees',
    'summary': """Company Visitors Pass & Details (Human Resource)""",
    'description': """
        HR Visitor Process module for company visit.
Tags:
company visitor
visitor process 
hr visitor process
visitor pass
visitor report
company visit
employee visitors
odoo visitor
visit company
pass print
    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': 'www.probuse.com',
    'images': ['static/description/image.jpg'],
    # 'live_test_url': 'https://youtu.be/_5xoD13CC68',
    'live_test_url' : 'https://probuseappdemo.com/probuse_apps/hr_visitor/1012',#'https://youtu.be/wE7VA7gGphA',
    'depends': ['hr'],
    'data': [
            'security/ir.model.access.csv',
            'security/security.xml',
            'datas/visitor_sequence.xml',
            'views/visitor_process.xml',
            'reports/visitor_report.xml',
            ],
    'installable': True,
    'application': False,
}

