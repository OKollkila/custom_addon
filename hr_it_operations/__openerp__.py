# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equipment Request & IT Operations',
    'version': '2.6',
    'price': 50.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Human Resources',
    'summary': 'Employee - Equipment Request & IT Operations (Human Resources)',
    'description': """ 
Equipment Request & IT Operations
Allow employee to request for hardware/software resource to HR department.
Allow employee to request for damage hardware and expense integrated with HR expenses.
Print PDF report of Equipments.
Equipments
hr stock
Equipment Maintanance
Repair Stock Management
Equipments
Equipment
Equipment Maintenance Software
Equipment management
Equipments/Equipments
maintenance request
employee maintenance request
maintenance stock
stock maintenance
Equipment Stock Management
employee stock
employee assets
employee Equipments
employee Equipment stock
Equipments/Equipments/Department Equipment Requests to Approve
Equipments/Equipments/HR Equipment Requests to Approve
Equipments/Equipments/My Equipment Requests
Equipments/Equipments/Stock Equipment Requests to Approve
employee hardware Equipment request
employee software Equipment request
it operations 
hr operations
human resource operation
employee expense damage

""",
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/hr_it_operations/752',#'https://youtu.be/PQP83dLonCw',
    'depends': ['stock','hr_expense'],
    'images': ['static/description/hritl.png'],
    'data': [
            'security/hr_it_operation_security.xml',
            'security/ir.model.access.csv',
            'views/it_operations_data.xml',
            'views/hr_it_operations.xml',
            'report/hr_it_operation_report.xml',
             ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
