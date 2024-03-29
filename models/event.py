import random

from odoo import models, fields, api, _
from markupsafe import Markup


class Event(models.Model):
    _name = 'comissions.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'comissions.utils']

    name = fields.Char(string='Name', required=True)
    program = fields.Many2one('student.program', string='Program')
    degree = fields.Many2one('student.degree', string='Degree', required=True)
    type = fields.Selection([('cw', 'Course Work (Курсовая работа)'), ('fqw', 'Final Qualifying Work (ВКР)')],
                            string="Proposal Project Type", required=True)
    matching_projects = fields.Many2many('student.project', string='Matching Projects')
    matching_professors = fields.Many2many('student.professor', string='Matching Professors')
    comissions = fields.One2many('comissions.comission', 'event_id', string='Commissions')
    manager_account = fields.Many2one('res.users', string='Manager Account', default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('created', 'Создано'),
        ('selection', 'Выбор'),
        ('distribution', 'Распределение'),
        ('defense', 'Защита'),
        ('done', 'Завершено'),
    ], string='Статус', default='draft')
    note = fields.Text(string='Note')
    # additional_files = fields.Many2many(
    #     comodel_name='ir.attachment',
    #     relation='event_additional_files_rel',
    #     column1='project_id',
    #     column2='attachment_id',
    #     string='Attachments'
    # )
    is_manager = fields.Boolean(compute='_is_manager')

    @api.model_create_multi
    def create(self, vals):

        matched_user = self.env['student.manager'].search([('manager_account', '=', self.env.user.id)])

        vals[0]['program'] = matched_user[0].program_ids[0].id

        record = super(Event, self).create(vals)
        matching_as = self.env['student.project'].search([
            ('proposal_id.type', '=', record.type),
            ('proposal_id.student_program', '=', matched_user[0].program_ids[0].name),
            ('proposal_id.proponent.degree.name', '=', record.degree.name)
        ])

        record.matching_projects = [(6, 0, matching_as.ids)]

        matching_as = self.env['student.professor'].search([
            ('professor_faculty.name', '=', record.program.program_faculty_id.name),
        ])

        record.matching_professors = [(6, 0, matching_as.ids)]

        record.state = 'created'

        return record


    def notify_professors(self):
        self.write({'state': 'selection'})

        # Send the email --------------------
        # subtype_id = self.env.ref('comissions.comissions_message_subtype_email')
        # template = self.env.ref('comissions.email_template_event_send')
        # template.send_mail(self.id, email_values={'subtype_id': subtype_id.id}, force_send=True)
        # -----------------------------------

        for professor in self.matching_professors:

            # Construct the message that is to be sent to the user
            message_text = f'<strong>Event invitation Received</strong><p> ' + self.manager_account.name + " sent an event «" + self.name + "». Please select date to join commission.</p>"

            # Use the send_message utility function to send the message
            self.env['comissions.utils'].send_message('event', Markup(message_text), professor.professor_account,
                                                   self.manager_account, (str(self.id), str(self.name)))



        return self.env['comissions.utils'].message_display('Sent', 'The event invitation is sent to professors.', False)

    def complete_comission_creating(self):
        self.write({'state': 'distribution'})

    def distribute_randomly(self):
        self.ensure_one()

        if not self.matching_projects:
            return

        projects = self.matching_projects

        random.shuffle(projects)

        comissions = self.comissions

        commissions_num = len(comissions)

        for index, project in enumerate(projects):
            commission = comissions[index % commissions_num]
            commission.student_works |= self.env['student.project'].browse(project.id)

        self.write({'state': 'defense'})

    @api.depends('name')
    def _is_manager(self):
        target_group_xml_id = 'student.group_manager'
        user_groups = self.env.user.groups_id
        target_group = self.env.ref(target_group_xml_id)
        for record in self:
            record.is_manager = target_group in user_groups
