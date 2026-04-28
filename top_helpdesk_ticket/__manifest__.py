{
    'name': 'Helpdesk Ticket  Check',
    'version': '1.0',
    'summary': 'Prevent duplicate helpdesk tickets with the same phone number within 24 hours',
    'description': """
This module prevents creating more than one helpdesk ticket with the same phone number within a 24-hour period.
    """,
    'category': 'Helpdesk',
    'author': 'topbusiness',
    'website': '',
    'depends': ['helpdesk', 'ramcrm'],
    'data': [
        'views/helpdesk_ticket_views.xml',
        'views/help_desk_team.xml',

          # ← مهم
    ],
    'assets': {
        'web.assets_backend': [
            # 'top_helpdesk_ticket/static/src/js/reload_action.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
