from odoo import http
from odoo.http import request


class LeadHistory(http.Controller):

    @http.route('/lead_history', type='json', auth="user")
    def history(self, id, limit=10, max_id=None, min_id=None):
        # Check if the user has access to the lead
        request.env['crm.lead'].browse(int(id)).check_access_rule('read')
        messages = (request.env['mail.message'].sudo()._message_fetch(domain=[
            ('res_id', '=', int(id)),
            ('model', '=', 'crm.lead'),
            ('message_type', '!=', 'user_notification'),
            ], before=max_id, after=min_id, limit=limit)['messages'].read(
                {
                    'body',
                    'author_id',
                    'date',
                    'message_type',
                    'subtype_id',
                    'tracking_value_ids'
                }
        ))
        for msg in messages:
            msg['tracking_value_ids'] = request.env['mail.tracking.value'].sudo().browse(msg['tracking_value_ids']).read(['create_uid', 'field_id', 'old_value_char', 'new_value_char'])
        return messages