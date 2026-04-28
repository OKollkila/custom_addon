{
    'name': 'Goinfinito SMS Integration',
    'version': '18.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Integrate Goinfinito SMS API for Helpdesk ticket notifications',
    'description': """
Goinfinito SMS Integration for Helpdesk
=======================================

This module integrates the Goinfinito SMS API to send automated SMS notifications
for Helpdesk tickets.

Features:
---------
* SMS notifications on ticket creation
* SMS notifications on ticket closure
* Configurable SMS templates (Arabic/English)
* Manual SMS sending from ticket form
* Company-specific configuration
* Secure API token storage
    """,
    'author': 'Top Systems',
    'website': 'https://www.top-systems.com',
    'depends': [
        'helpdesk',
        'base',
        'ramcrm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/template_data.xml',
        'views/top_goinfinito_config_views.xml',
        'views/top_goinfinito_template_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_ticket_type_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

