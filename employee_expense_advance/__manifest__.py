# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Expense Advance Request - Employee',
    'version': '1.0',
    'price': 55.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Human Resources',
    'summary': 'Allow employee to request expense in advance.',
    'description': """
        Employee Advance Expense Requests:
Expense Advance Request - Employee
Expense Advance
Created Menus :
employee Expense Advance
advance
employee advance
Expenses/Expense Advances
Expenses/Expense Advances/Expense Advance Requests
Expenses/Expense Advances/Advance to Approve
Expenses/Expense Advances/Advance to Pay
Defined Reports

Print Advance Expense
This module allow your employees to create advance request for expenses. This module will work with multi currency.
Note: We have not changed any accounting entries for expense or expense sheet, we are just showing advance taken for that expense by employee
Employee advance expense
Expense Advance Request - Employee
advance expense
expense request
advance request
accounting expense
employee advance expense process
director expense approval
Employee Advance Expense Request 
Employee Advance Expense Request PDF Report
Employee Advance Expense Request QWEB Report
hr employee advance
cash advance
expense advance
advance form
advance request
advance application form
employee advance request
hr_expense
hr_expense_advance
hr_advance
hr expense
hr advance
expense advance form

Employee advance salary
advance salary
salary advance
advance employee
salary advance
employee advance
salary request
advance request
payroll salary
accounting salary
Salary Advances
Salary Advance
Employee Cash Advances
Employee Cash Advance
employee_advance_salary
employee advance salary process
director salary approval
advance request
cash advance
employee cash advance
salary in advance
employee salary
hr payroll
payroll employee
employee hr payroll
payroll

            """,
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'depends': ['hr_expense'],
    # 'live_test_url': 'https://youtu.be/Mty6cj6O6Xw',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/employee_expense_advance/985',#'https://youtu.be/N1ubbbvC_iA',
    'data': ['security/employee_advance_expense_security.xml',
             'security/ir.model.access.csv',
             'data/expense_sequence_data.xml',
             'views/employee_advance_expense.xml',
             'views/hr_expense.xml',
             'views/advance_expense_sheet.xml',
             'report/employee_advance_expense_report.xml'
             ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
