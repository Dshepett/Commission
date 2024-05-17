from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError, AccessError
import xlsxwriter
import base64
import os

class Comission(models.Model):
    _name = 'comissions.comission'
    _description = 'Commission'

    name = fields.Char(string='Name', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    event_id = fields.Many2one('comissions.event', string='Event', required=True)

    user_ids = fields.One2many('comissions.comission_professor', 'comission_id', string='Joined Professors')
    approved_user_ids = fields.Many2many('student.professor', string='Approved Professors',relation='comission_approved_user_rel',
                                         column1='comission_id',column2='user_id')

    student_works = fields.Many2many('student.project', string='Student Projects')

    report_file = fields.Binary(string='Report File')
    note = fields.Text(string='Note')
    additional_files = fields.Many2many(
        comodel_name='ir.attachment',
        relation='commissions_commission_additional_files_rel',
        column1='commission_id',
        column2='attachment_id',
        string='Attachments'
    )

    is_manager = fields.Boolean(compute='_is_manager')
    @api.depends('user_ids')
    def _is_manager(self):
        target_group_xml_id = 'student.group_manager'
        user_groups = self.env.user.groups_id
        target_group = self.env.ref(target_group_xml_id)
        for record in self:
            record.is_manager = target_group in user_groups

    @api.constrains('start_date','end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_('Start date must be less than end date.'))
            if record.start_date < record.event_id.deadline:
                raise ValidationError(_('Commission dates must be greater than event deadline.'))

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

            return self.env['comissions.utils'].message_display('Joined', f'You are joined to commission "{self.name}"',
                                                                False)

    def generate_report(self):
        report_name = f'report_{self.name}.xlsx'
        workbook = xlsxwriter.Workbook(report_name)

        worksheet = workbook.add_worksheet()

        worksheet.write(0, 0, 'Name')
        worksheet.write(0, 1, self.name)
        worksheet.write(1, 0, 'Start time')
        worksheet.write(1, 1, self.start_date.strftime('%Y-%m-%d %H:%M'))
        worksheet.write(1, 2, 'End time')
        worksheet.write(1, 3, self.end_date.strftime('%Y-%m-%d %H:%M'))

        worksheet.write(3,0,'Professors')

        curr_row = 4

        for user in self.approved_user_ids:
            worksheet.write(curr_row,0,user.name)
            curr_row += 1

        curr_row+=1
        worksheet.write(curr_row,0,'Projects')

        curr_row += 1
        worksheet.write(curr_row, 0, 'Name')
        worksheet.write(curr_row, 1, 'Student')
        worksheet.write(curr_row, 2, 'Grade')

        curr_row += 1

        for project in self.student_works:
            worksheet.write(curr_row,0,project.name)
            worksheet.write(curr_row,1,project.proposal_id.proponent.name)
            worksheet.write(curr_row,2,project.grade)
            curr_row += 1

        workbook.close()

        with open(report_name, 'rb') as file:
            file_data = file.read()
        self.report_file = base64.b64encode(file_data)

        os.remove(report_name)

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/comissions.comission/%s/report_file/%s?download=true' % (
                self.id, report_name),
        }

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
        return self.env['comissions.utils'].message_display('Approved', f'Professor {self.professor_id.name} is approved for comission "{self.comission_id.name}"',
                                                            False)