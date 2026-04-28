{
    'name': 'CZDboard',
    'version': '1.0',
    'depends': ['base', 'web', 'crm', 'ramcrm'],
    'data': [
        'security/security.xml',        # انقلته هنا وخليته أول واحد
        'security/ir.model.access.csv',
        'views/dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # شلت الـ security.xml من هنا لأنه مكانه غلط
            'CZDboard/static/src/js/dashboard.js',
            'CZDboard/static/src/xml/dashboard.xml',
            'CZDboard/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
}