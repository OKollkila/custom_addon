# -*- coding: utf-8 -*-
{
    'name': "CliniZone Reviews",

    'summary': "Reviews of the service provided by the medical center",

    'description': """
Reviews of the service provided by the medical center using WhatsApp
    """,

    'author': "Surge Technologies",
    'website': "https://surge.com.eg",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2',
    'license': 'Other proprietary',

    # any module necessary for this one to work correctly
    'depends': ['base', 'ramcrm', 'cz_prime_care', 'survey', 'surge_unifonic', 'surge_surveys'],

    # always loaded
    'data': [
        'data/groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/checkout/tree.xml',
        'views/checkout/form.xml',
        'views/checkout/action.xml',
        'views/checkout/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

