
{
    'name': "top Employee Attendance Xlsx Report",
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': """This module will manage  the attendance report of employees 
    in xlsx""",
    'description': """This module helps to generate the attendance report of 
    employees in the XLSX format""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['hr_attendance'],
    'data': [
        # 'security/ir.model.access.csv',
        'wizards/employee_attendance_report_views.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'top_hr_attendance_xlsx_report/static/src/js/action_manager.js',
    #     ]
    # },
    # 'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
