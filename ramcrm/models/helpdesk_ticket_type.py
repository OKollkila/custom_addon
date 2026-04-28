from odoo import models, fields


class HelpdeskType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Helpdesk Ticket Type'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    def init(self):
        self.env.cr.execute('SELECT count(*) FROM helpdesk_ticket_type WHERE id = 14')
        res = self.env.cr.fetchone()
        if res and res[0] > 0:
            return

        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 1'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 2'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 3'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 4'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 5'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 6'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 7'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 8'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 9'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 10'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 11'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 12'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 13'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 14'})
        self.env['helpdesk.ticket.type'].create({'name': 'DUMMY 15'})
        self.env.cr.commit()