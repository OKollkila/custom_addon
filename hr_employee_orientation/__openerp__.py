# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Orientation Process (Human Resource)',
    'version': '1.1',
    'price': 15.0,
    'currency': 'EUR',
    'category': 'Human Resources',
    'summary': 'Employee Orientation Process - Human Resource',
    'description': """
        Employee Orientation process:

Employee orientation is part of a long-term investment in a new employee. It is an initial process that provides easy access to basic information, programs and services, gives clarification and allows new employees to take an active role in their organization.

Workflow:

HR Officer/Manager create Employee orientation (Orientations/Employee Orientations) for new employee coming in organization and by selecting orientation checklist field on orientation form that time it will fill all orientation checklist lines automatically... Now once HR Officer/Manager confirm Employee orientation that time system will create Checklist requests and allocate jobs to responsible person assosicated with that checklist/task.(Orientations/Orientation Checklists Requests)

Now when responsible person login in system, he/she will find job allocated under Orientations/Orientation Checklists Requests and finish it.

Note that Orientation Checklist Configuration will be configured by department, for example new comer join IT department then he/she has going to process under Orientation Checklist Configuration of IT department...

This module allow you to manage employee orientation process

  * Employee Orientations

  * Orientation Checklists Requests

  * Configurations 

Menus:

Orientations
Orientations/Employee Orientations
Orientations/Orientation Checklists Requests
Orientations/Configurations
Orientations/Configurations/Orientation Checklists
Orientations/Configurations/Orientation Checklists Lines

New Employee Orientation
Effectively orienting new employees to the campus and to their positions is critical to establishing successful, productive working relationships. The employee's first interactions with you should create a positive impression of your department and the campus. The time you spend planning for the new person's first days and weeks on the job will greatly increase the chance for a successful start.

An effective orientation will:

- Foster an understanding of the campus culture, its values, and its diversity

- Help the new employee make a successful adjustment to the new job

- Help the new employee understand his/her role and how he/she fits into the total organization

- Help the new employee achieve objectives and shorten the learning curve

- Help the new employee develop a positive working relationship by building a foundation of knowledge about campus mission, objectives, policies, organization structure, and functions




            """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'support': 'contact@probuse.com',
    'live_test_url': 'https://youtu.be/RHwx24QwOk8',
    'images': ['static/description/img1.jpg'],
    'depends': ['hr'],
    'data': [
             'security/employee_orientation_security.xml',
             'security/ir.model.access.csv',
             'data/employee_orientation_data.xml',
             'data/employee_orientation_sequence.xml',
             'views/employee_orientation.xml',
             ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
