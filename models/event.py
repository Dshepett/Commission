import random

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from markupsafe import Markup
from datetime import datetime, timedelta


class Event(models.Model):
    _name = 'comissions.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'comissions.utils']

    name = fields.Char(string=_('Name'), required=True)
    program = fields.Many2one('student.program', string=_('Program'))
    degree = fields.Many2one('student.degree', string=_('Degree'), required=True)
    type = fields.Selection([('cw', 'Course Work (Курсовая работа)'), ('fqw', 'Final Qualifying Work (ВКР)')],
                            string=_("Proposal Project Type"), required=True)

    matching_projects = fields.Many2many('student.project', string=_('Matching Projects'))
    matching_professors = fields.Many2many('student.professor', string=_('Matching Professors'))
    comissions = fields.One2many('comissions.comission', 'event_id', string=_('Commissions'))

    manager_account = fields.Many2one('res.users', string='Manager Account', default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('created', 'Создано'),
        ('selection', 'Выбор'),
        ('distribution', 'Распределение'),
        ('defense', 'Защита'),
        ('done', 'Завершено'),
    ], string='Статус', default='draft')
    deadline = fields.Datetime(string=_('Deadline'))

    note = fields.Text(string=_('Note'))
    additional_files = fields.Many2many(
        comodel_name='ir.attachment',
        relation='commissions_event_additional_files_rel',
        column1='event_id',
        column2='attachment_id',
        string=_('Attachments')
    )

    is_manager = fields.Boolean(compute='_is_manager')
    selection_complete = fields.Boolean(compute='_selection_complete')
    notifcation_done = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals):
        matched_user = self.env['student.manager'].search([('manager_account', '=', self.env.user.id)])
        if not matched_user:
            raise AccessError(_('Only managers can create events.'))

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

    @api.constrains('deadline')
    def _check_deadline(self):
        for record in self:
            if record.deadline and record.deadline < fields.Datetime.now():
                raise ValidationError(_('Deadline must be greater than current date.'))

    @api.constrains('comissions')
    def _check_comissions(self):
        for record in self:
            if len(record.comissions) == 0:
                raise ValidationError(_('Event must have at least one commission.'))

    def close_selection(self):
        records_to_update = self.search([('state', '=', 'selection'), ('deadline', '<=', fields.Datetime.now())])
        records_to_update.write({'state': 'distribution'})

    def notify_professors(self):
        self.write({'state': 'selection'})

        subtype_id = self.env.ref('comissions.comissions_message_subtype_email')
        template = self.env.ref('comissions.email_template_event_send')
        template.send_mail(self.id, email_values={'subtype_id': subtype_id.id}, force_send=True)

        professor_ids = [professor.professor_account for professor in self.matching_professors]
        message_text = _('<strong>Event invitation Received</strong><p> %s created event «%s». Please select date to '
                         'join commission.</p>', self.manager_account.name, self.name)

        self.env['comissions.utils'].send_message('event', Markup(message_text), professor_ids,
                                                      self.manager_account, (str(self.id), str(self.name)))

        return self.env['comissions.utils'].message_display(_('Sent'), _('The event invitation is sent to professors.'),
                                                            False)

    def notify_professors_deadline_task(self):
        events = self.search([('deadline', '!=', False), ('notifcation_done', '=', False)])
        now = datetime.now()
        for event in events:
            deadline = fields.Datetime.from_string(event.deadline)
            if deadline - now < timedelta(days=1):
                event.notify_professors_deadline()

    def notify_professors_deadline(self):
        subtype_id = self.env.ref('comissions.comissions_message_subtype_email')
        template = self.env.ref('comissions.email_template_event_selection_needed')
        template.send_mail(self.id, email_values={'subtype_id': subtype_id.id}, force_send=True)

        professor_ids = [professor.professor_account for professor in self.matching_professors]

        message_text = _('<strong>Comission selection ends soon</strong><p> %s created event «%s». You have only one day '
                         'to select commission.</p>', self.manager_account.name, self.name)

        self.env['comissions.utils'].send_message('event', Markup(message_text), professor_ids,
                                                  self.manager_account, (str(self.id), str(self.name)))

        self.notifcation_done = True

    def complete_commission_creating(self):
        self.write({'state': 'distribution'})
        return self.env['comissions.utils'].message_display(_('Done'), _('Commission distribution done.'),
                                                            False)

    def commissions_availability(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        visit_table_url = '/visit_table/%s' % self.id
        return {'type': 'ir.actions.act_url',
                'url': base_url + visit_table_url,
                'target': 'new',
                }

    def distribute_randomly(self):
        self.ensure_one()

        if not self.matching_projects:
            return

        projects = list(self.matching_projects)

        random.shuffle(projects)

        return self.distribute_sorted_works(projects)

    def distribute_by_name(self):
        self.ensure_one()

        if not self.matching_projects:
            return

        projects = list(self.matching_projects)

        projects.sort(key=lambda x: x.name)

        return self.distribute_sorted_works(projects)

    def distribute_by_student_name(self):
        self.ensure_one()

        if not self.matching_projects:
            return

        projects = list(self.matching_projects)

        projects.sort(key=lambda x: x.proposal_id.proponent.name)

        return self.distribute_sorted_works(projects)

    def distribute_sorted_works(self, projects):
        commissions = self.comissions

        commissions_num = len(commissions)

        for index, project in enumerate(projects):
            commission = commissions[index % commissions_num]
            commission.student_works |= self.env['student.project'].browse(project.id)

        self.write({'state': 'defense'})

        return self.env['comissions.utils'].message_display(_('Distributed'), _('Works distributed.'),
                                                            False)

    @api.depends('name')
    def _is_manager(self):
        target_group_xml_id = 'student.group_manager'
        user_groups = self.env.user.groups_id
        target_group = self.env.ref(target_group_xml_id)
        for record in self:
            record.is_manager = target_group in user_groups

    def _selection_complete(self):
        self.selection_complete = self.state == 'done' or self.state == 'distribution' or self.state == 'defense'
