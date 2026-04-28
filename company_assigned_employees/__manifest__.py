# -*- coding: utf-8 -*-
{
    'name': 'Company Assigned Employees',
    'version': '18.0.1.0.0',
    'summary': 'Extend res.company with assigned employees field',
    'description': """
Company Assigned Employees
==========================

This module extends the company model to include a many2many field for assigned employees.

Features:
---------
* Add 'Assigned Employees' field to company configuration
* Many2many relationship with hr.employee
* Tags widget for easy employee selection
* Company-specific employee assignments

Technical:
----------
* Extends res.company model
* Inherits company form view
* Compatible with Odoo 18.0
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Human Resources/Employees',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
    ],
    'data': [
        'views/res_company_views.xml',
    ],
    'demo': [],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 100,
}
