{
    'name': 'Helpdesk All Tickets Readonly',
    'version': '18.0.1.0.0',
    'category': 'Helpdesk',
    'summary': 'Adds a read-only menu to view all helpdesk tickets',
    'description': """
        This module adds a new menu item "All Tickets (Readonly)" 
        under Helpdesk to view all tickets in read-only mode .
    """,
    'author': 'TopBusiness',
    'depends': ['helpdesk'],
    'data': [
        # 'views/helpdesk_all_tickets_view.xml',
        # 'views/helpdesk_ticket_readonly_views.xml',
        'security/ir.model.access.csv',
        'views/all_tickets.xml',
    ],
    'installable': True,
    'application': False,
}
