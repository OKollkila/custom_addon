# -*- coding: utf-8 -*-
{
    'name': 'Top API',
    'version': '18.0',
    'author': 'top Business',
    'maintainer': 'top  Business',
    'category': 'Custom',
    'depends': ['base', 'crm', 'hr', 'web', 'helpdesk', 'ramcrm'],
    'data': [
        'data/ir_cron_data.xml',
        'data/ir_cron_data_promotion.xml',
        'security/helpdesk_team_read_all_companies.xml',
        'views/crm.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
