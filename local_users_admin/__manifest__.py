{
    'name': 'Local Users Admin',
    'license': 'Other proprietary',
    'summary': 'Local Users Admin',
    'version': '0.1',
    'description': """ Local Users Admin """,
    'depends': ['web', 'mail'],
    'data': [
        'data/groups.xml',
        'views/user_form.xml',
        'views/user_tree.xml',
        'views/user_action.xml',
        'views/menu.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/allowed_group/allowed_groups_tree.xml',
        'views/allowed_group/allowed_groups_action.xml',
        'views/allowed_group/allowed_groups_menu.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
}
