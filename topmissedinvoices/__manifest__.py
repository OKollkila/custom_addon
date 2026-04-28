# -*- coding: utf-8 -*-
{
    'name': 'Top Missed Invoices',
    'version': '18.0.1.0.0',
    'category': 'CRM',
    'summary': 'Module to fetch rejected services from webhook and create CRM leads',
    'description': """
        This module integrates with the Prime Care API to fetch rejected services
        and automatically creates CRM leads for follow-up.
    """,
    'author': 'Top Business',
    'website': 'https://www.clinizone.com',
    'depends': [
        'base',
        'crm',
        'utm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/utm_data.xml',
        'data/ir.config_parameter.xml',
        'views/top_missed_invoice_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
