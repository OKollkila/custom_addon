from odoo import models, fields, api

class SurveyTeam(models.Model):
    _name = 'survey.team'
    _description = 'Survey Team'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    member_ids = fields.Many2many('res.users', 'survey_team_users_rel', 'team_id', 'user_id', string='Members')
    survey_ids = fields.One2many('survey.survey', 'team_id', string='Surveys')

    @api.model
    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

class Survey (models.Model):
    _inherit = 'survey.survey'

    team_id = fields.Many2one('survey.team', string='Team')