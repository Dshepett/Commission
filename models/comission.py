from odoo import models, fields, api


class Comission(models.Model):
    _name = 'comissions.comission'
    _description = 'Commission'

    name = fields.Char(string='Name', required=True)
    date = fields.Datetime(string='Date', required=True)
    event_id = fields.Many2one('comissions.event', string='Event', required=True)
    user_ids = fields.One2many('comissions.comission_professor', 'comission_id', string='Joined Professors')
    approved_user_ids = fields.Many2many('student.professor', string='Approved Professors',relation='comission_approved_user_rel',
                                         column1='comission_id',column2='user_id')
    student_works = fields.Many2many('student.project', string='Student Projects')
    is_manager = fields.Boolean(compute='_is_manager')
    note = fields.Text(string='Note')
    # additional_files = fields.Many2many(
    #     comodel_name='ir.attachment',
    #     relation='commission_additional_files_rel',
    #     column1='project_id',
    #     column2='attachment_id',
    #     string='Attachments'
    # )

    @api.depends('user_ids')
    def _is_manager(self):
        target_group_xml_id = 'student.group_manager'
        user_groups = self.env.user.groups_id
        target_group = self.env.ref(target_group_xml_id)
        for record in self:
            record.is_manager = target_group in user_groups

    def add_user(self):
        self.ensure_one()
        current_user = self.env.uid

        professor = self.env['student.professor'].search([('professor_account', '=', current_user)], limit=1)

        exists = self.user_ids.filtered(lambda x: x.professor_id == professor.id)

        if not exists:
            self.user_ids.create({
                'professor_id': professor.id,
                'comission_id': self.id
            })

class CommissionProfessor(models.Model):
    _name = 'comissions.comission_professor'
    _description = 'Commission Professor'

    professor_id = fields.Many2one('student.professor', string='Professor', required=True)
    comission_id = fields.Many2one('comissions.comission', string='Comission', required=True)
    approved = fields.Boolean(string='Approved', default=False)

    def approve(self):
        self.ensure_one()
        self.write({'approved': True})
        self.comission_id.approved_user_ids |= self.professor_id