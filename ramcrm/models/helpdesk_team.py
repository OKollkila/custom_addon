from odoo import models, fields


class HelpdeskTeam(models.Model):
    _name = 'helpdesk.team'
    _inherit = 'helpdesk.team'

    escalate_team_id = fields.Many2one('helpdesk.team')
    escalate_after = fields.Integer(string='Escalate After (hours)', default=24)
    escalate_after_minutes = fields.Integer(string='Escalate After (Minutes)', default=24 * 60, store=True, compute='_compute_escalate_after_minutes', readonly=False)
    escalate_after_display = fields.Char(string='Escalate After (Hours)', compute='_compute_escalate_after_display')

    def _compute_escalate_after_minutes(self):
        for team in self:
            team.escalate_after_minutes = team.escalate_after * 60

    def _compute_escalate_after_display(self):
        for team in self:
            team.escalate_after_display = '%02d:%02d' % divmod(team.escalate_after_minutes, 60)