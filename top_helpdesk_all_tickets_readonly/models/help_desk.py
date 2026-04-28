from odoo import models, fields, tools, api

class HelpdeskTicketAll(models.Model):
    _name = 'helpdesk.ticket.all'
    _description = 'All Helpdesk Tickets (Read Only)'
    _auto = False

    ticket_ref = fields.Char()
    name = fields.Char()
    priority = fields.Selection([
        ('0', 'Very Low'),
        ('1', 'Low'),
        ('2', 'Medium'),
        ('3', 'High')
    ])
    team_id = fields.Many2one('helpdesk.team')
    user_id = fields.Many2one('res.users', string="Assigned to")
    partner_id = fields.Many2one('res.partner', string="Customer")
    sla_deadline = fields.Datetime()
    create_date = fields.Datetime()
    write_date = fields.Datetime()
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('blocked', 'Blocked'),
        ('done', 'Ready for next stage')
    ])
    stage_id = fields.Many2one('helpdesk.stage', string="Stage", tracking=True)
    description = fields.Html()
    company_id = fields.Many2one('res.company')

    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Ticket Type")
    case_no = fields.Char(string="Case No")

    reporter_relation_with_patient = fields.Selection([
        ('SELF', 'Self'),
        ('FATHER', 'Father'),
        ('MOTHER', 'Mother'),
        ('RELATIVE', 'Relative'),
        ('FRIEND', 'Friend'),
        ('OTHER', 'Other'),
    ], string="Reporter Relation with Customer")

    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    national_id = fields.Char(string="National ID")
    medical_file_no = fields.Char(string="Medical File No")
    case_time = fields.Datetime(string="Case Time")

    branch_id = fields.Many2one('res.branch', string="Branch")
    city_final = fields.Char(string="City Final")

    # ✅ Dynamic readonly fields
    tag_ids = fields.Many2many('helpdesk.tag', compute='_compute_dynamic_fields', store=False)
    sla_status_ids = fields.Many2many('helpdesk.sla.status', compute='_compute_dynamic_fields', store=False)
    activity_ids = fields.One2many('mail.activity', 'res_id', compute='_compute_dynamic_fields', store=False)

    # ✅ Chatter-related fields
    message_ids = fields.One2many('mail.message', 'res_id', compute='_compute_dynamic_fields', store=False)
    message_follower_ids = fields.One2many('mail.followers', 'res_id', compute='_compute_dynamic_fields', store=False)

    @api.depends_context('uid')
    def _compute_dynamic_fields(self):
        Ticket = self.env['helpdesk.ticket'].sudo()
        for record in self:
            ticket = Ticket.browse(record.id)
            record.tag_ids = ticket.tag_ids
            record.sla_status_ids = ticket.sla_status_ids
            record.activity_ids = ticket.activity_ids
            record.message_ids = ticket.message_ids
            record.message_follower_ids = ticket.message_follower_ids

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW helpdesk_ticket_all AS (
                SELECT 
                    id,
                    ticket_ref,
                    name,
                    priority,
                    team_id,
                    user_id,
                    partner_id,
                    sla_deadline,
                    create_date,
                    write_date,
                    kanban_state,
                    stage_id,
                    company_id,
                    description,
                    ticket_type_id,
                    case_no,
                    partner_email AS email,
                    partner_phone AS phone,
                    patient_national_id AS national_id,
                    medical_file_no,
                    case_time
                FROM helpdesk_ticket
            )
        """)


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    def action_readonly_tickets(self):
        action = self.env.ref("helpdesk.helpdesk_ticket_action_main_tree").read()[0]
        action['name'] = "Tickets Readonly"
        action['context'] = dict(self.env.context, create=False, edit=False, delete=False, readonly=True)
        return action
