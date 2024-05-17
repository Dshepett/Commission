{
    'name': 'Commissions organization',
    'author': 'Dshepett',
    'category': 'Human Resources/Student',
    'summary': 'Organize commissions',
    'depends': ['mail', 'student', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/event.xml',
        'views/comission.xml',
        'views/email_templates.xml',
        'views/utils.xml',
        'views/professor_availability_template.xml',
    ],
    'installable': True,
    'application': True,
}