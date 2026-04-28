from odoo import models, fields, tools


class HelpdeskTicketReport(models.Model):
    _name = 'helpdesk.ticket.report.analysis'
    _inherit = 'helpdesk.ticket.report.analysis'

    branch_id = fields.Many2one('clinizone.branch', string='Branch', readonly=True)

    def _select(self):
        select_str = """
            SELECT T.id AS id,
                   T.id AS ticket_id,
                   T.create_date AS create_date,
                   T.priority AS priority,
                   T.user_id AS user_id,
                   T.partner_id AS partner_id,
                   T.ticket_type_id AS ticket_type_id,
                   T.stage_id AS ticket_stage_id,
                   T.branch_id AS branch_id,
                   T.sla_deadline AS ticket_deadline,
                   NULLIF(T.close_hours, 0) AS ticket_close_hours,
                   EXTRACT(EPOCH FROM (COALESCE(T.close_date, NOW() AT TIME ZONE 'UTC') - T.create_date)) / 3600 AS ticket_open_hours,
                   NULLIF(T.assign_hours, 0) AS ticket_assignation_hours,
                   T.close_date AS close_date,
                   T.assign_date AS assign_date,
                   NULLIF(T.rating_last_value, 0) AS rating_last_value,
                   T.active AS active,
                   T.team_id AS team_id,
                   T.company_id AS company_id,
                   T.kanban_state AS kanban_state
        """
        return select_str

    def _from(self):
        from_str = """
            helpdesk_ticket T
        """
        return from_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            )""" % (self._table, self._select(), self._from()))