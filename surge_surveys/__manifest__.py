{
    'name': "Survey Teams",
    'summary': "Teams in the Surveys module",
    'description': """
This module adds teams to the Surveys module.
    """,
    'author': "Surge Technologies",
    'license': 'Other proprietary',
    'website': "https://surge.com.eg",
    'category': 'Uncategorized',
    'version': '0.2',
    'depends': ['base', 'survey'],
    'data': [
        'data/ir.model.access.csv',
        'data/rule_survey.xml',
        'views/menu.xml',
        'views/team/list.xml',
        'views/team/form.xml',
        'views/team/action.xml',
        'views/team/menu.xml',
        'views/survey/form.xml',
    ],
    'demo': [
    ],
}

