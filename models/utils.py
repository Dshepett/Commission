from odoo import api, fields, models, _
from markupsafe import Markup

class Utils(models.AbstractModel):
    _name = 'comissions.utils'
    _description = 'Comissions - Utility Methods'

    @api.model
    def send_message(context, source, message_text, recipients, author, data_tuple = -1):
        tuple_id, tuple_name = data_tuple

        if source == 'event':
            channel_name = "Event \"" + tuple_name + "\""
        elif source == 'comission':
            channel_name = "Comission №" + tuple_id + " for " + tuple_name
        else:
            channel_name = source + " №" + id

        channel = context.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1, )

        if not channel:
            channel = context.env['discuss.channel'].with_context(mail_create_nosubscribe=True).sudo().create({
                'channel_partner_ids': [(6, 0, author.id + 1)],
                'channel_type': 'channel',
                'name': channel_name,
                'display_name': channel_name
            })

            channel.write({
                'channel_partner_ids': [(4, recipient.id + 1) for recipient in recipients]
            })

        # Send a message to the related user
        channel.sudo().message_post(
            body=Markup(message_text),
            author_id=author.id + 1,
            message_type="comment",
            subtype_xmlid='mail.mt_comment'
        )

    def message_display(self, title, message, sticky_bool):
        return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': _(title),
				'message': message,
				'sticky': sticky_bool,
				'next': {
					'type': 'ir.actions.act_window_close',
				}
			}
		}