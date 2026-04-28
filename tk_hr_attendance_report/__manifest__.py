# -*- coding: utf-8 -*-
{
    'name': 'HR Attendance Report | Attendance Detailed Report',
    'description': """
              HR Attendance Report
    """,
    'summary': 'HR Attendance Report',
    'version': '1.0',
    'category': 'HR',
    'author': 'TechKhedut Inc.',
    'company': 'TechKhedut Inc.',
    'maintainer': 'TechKhedut Inc.',
    'website': "https://techkhedut.com",
    'depends': [
        'hr', 'hr_attendance', 'hr_holidays',
    ],
    'data': [
        # security
        'security/ir.model.access.csv',
        # report
        'report/employee_attendance_pdf_report_views.xml',
        # wizard
        'wizard/employee_attendance_report_views.xml',
        #  views
        'views/hr_employee_menu.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
