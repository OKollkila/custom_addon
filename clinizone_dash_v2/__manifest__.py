{
    'name': 'CliniZone Dash V2',  # اسم جديد يظهر في قائمة التطبيقات
    'version': '1.0',
    'category': 'Dashboard',
    'depends': ['base', 'web', 'crm', 'ramcrm'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # تغيير المسارات لاسم المجلد الجديد
            'clinizone_dash_v2/static/src/js/dashboard.js',
            'clinizone_dash_v2/static/src/xml/dashboard.xml',
            'clinizone_dash_v2/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
}