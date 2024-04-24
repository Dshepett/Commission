{
    'name': 'Commissions organization',
    'author': 'Dshepett',
    'category': 'Human Resources/Student',
    'summary': 'Organize commissions',
    'depends': ['mail', 'student'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/event.xml',
        'views/comission.xml',
        'views/email_templates.xml',
        'views/regulations.xml'
    ],
    'installable': True,
    'application': True,
}