# -*- coding: utf-8 -*-
{
    'name': 'Top HR API',
    'version': '18.0',
    'author': 'top Business',
    'maintainer': 'top Business',
    'category': 'Custom',
    'depends': ['base', 'hr', 'web', 'base_geolocalize', 'hr_attendance'],
    'data': [
        'views/res_partner_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
