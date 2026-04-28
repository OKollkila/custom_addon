{
    'name': 'TOP RAM API Integration',
    'version': '18.0.1.2.0',
    'category': 'Services/Helpdesk',
    'summary': 'Integrate Helpdesk with RAM Prime Care API + Toast Notifications',
    'description': """
        This module extends Helpdesk tickets to integrate with RAM Prime Care API.
        - Adds workflow_level field to helpdesk tickets
        - Automatically calls external API when ticket stage changes
        - Real-time toast notifications for API sync status
        - Sends ticketId, workFlowLevel, status, and updateTime to external system
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'helpdesk',
        'ramcrm',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/ir_rule_data.xml',
        'data/system_parameters.xml',
        'data/workflow_level_data.xml',
        'data/workflow_level_cron.xml',
        'views/workflow_level_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/clinizone_branch_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

