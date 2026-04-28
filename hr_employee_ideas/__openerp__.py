# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Employee Ideas",
    'summary':  "Human Resource - Employee Ideas & Votes",
    'description': """
        HR Employee Ideas Modules:
        - Employee can post the idea and also employees vote for this idea.

ideas
Employee ideas
employee votes
ideas and votes
human resource employee ideas
hr ideas
hr_ideas
employee_ideas
Close the Idea
idea rate
idea Rating
idea Ratings
best idea
HR Idea Junction
Receive Votes
company ideas
employee idea
idea share
Idea_junction
idea junction
company votes
    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "www.probuse.com",
    'category': 'Human Resources',
    'price': 25.0,
    'currency': 'EUR',
    'version': '1.2.3',
    'depends': ['hr'],
    'data': [
            'security/ir.model.access.csv',
            'security/employee_ideas_security.xml',
            'wizard/ideas_review.xml',
            'views/employee_ideas.xml',
            'report/voting_reports.xml',
            'data/ideas_sequence.xml',
            ],
    'installable': True,
    'images': ['static/description/11111.png'],
    'live_test_url': 'https://youtu.be/0sjrjbKIe5E',
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
