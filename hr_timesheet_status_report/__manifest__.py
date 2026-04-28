# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.
{
    'name': 'Timesheet Incomplete Report Employees',
    'price': 49.0,
    'currency': 'EUR',
    'version': '1.0',
    'category': 'Services/Timesheets',
    'license': 'Other proprietary',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/hr_timesheet_status_report/761',#'https://youtu.be/ydrS2gZ2Rf8',
    'summary': 'This app allow you to print timesheet incomplete report and cron job allow to auto send weekly.',
    'description': """
incomplete timesheet
missing timesheet
not complete timesheet
Pending time sheet report (Frequency every week) : 
Report to be emailed to HR Manager and hierarchy of all managers. Better we can select and set default all followers who received.
If employee weekly timesheet not filled or not validated it will weekly report generated and send to managers
This module allows Timesheet Manager to print Timesheet Report.
Timesheet Employee Weekly Report
print Timesheet PDF Report
Timesheet Report PDF
Timesheet QWEB Report
This module allows Timesheet Manager to print Weekly Timesheet Report.
week timesheet
weekly timesheet
employee timesheet
employee week timesheet
employee weekly timesheet
timesheet pdf report
timesheet report
customer timesheet report
Timesheet Incomplete Report Employees

Notification Report Managers List

Cron Job to Send Report Weekly to All Managers Configured on Company Settings


customer timesheet
timesheet employee pdf
employee print timesheet
* INHERIT res.company.form.timesheet.followers (form)
HR Timesheet Report Form View (form)
report_hr_timesheet (qweb)
print odoo timesheet
probuse
timesheet
timesheet pdf report
weekly
week
timesheet week
analytic line
hr timesheet sheet
timesheet by project
timesheet line by project
timesheet line on project
project on timesheet
timesheet sheet
timesheet sheet employee
timesheet report to customer
timesheet activities
my timesheet
                    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/img.jpg'],
    'depends': [
        'hr_timesheet_attendance',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/company_views.xml',
        'report/report_hr_timesheet.xml',
        'data/timesheet_reminder_data.xml',
        'wizard/hr_timesheet_report_wizard.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
