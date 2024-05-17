from odoo import http
from odoo.http import request


class VisitTableController(http.Controller):

    @http.route('/visit_table/<model("comissions.event"):event>', auth='public', website=True)
    def visit_table(self, event, **kwargs):
        commissions = event.comissions
        professors = event.matching_professors

        table_data = []
        for professor in professors:
            row = {'professor': professor.name}
            for commission in commissions:
                visits = commission.user_ids.filtered(lambda v: v.professor_id == professor)
                if visits:
                    row[commission.name] = 'Yes' if visits[0].available else 'No'
                else:
                    row[commission.name] = 'No'
            table_data.append(row)

        return request.render('comissions.template_visit_table', {
            'event': event,
            'commissions': commissions,
            'table_data': table_data
        })