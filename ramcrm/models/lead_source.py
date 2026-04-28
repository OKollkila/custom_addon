from odoo import models, fields

class LeadSource(models.Model):
    _name = 'clinizone.lead_source'
    _description = 'Lead Source'

    name = fields.Char("Name", required=True)
    can_be_selected = fields.Boolean("Can be selected", default=False)
    parent_id = fields.Many2one('clinizone.lead_source', string='Parent Source')
    child_ids = fields.One2many('clinizone.lead_source', 'parent_id', string='Sub Sources')
    level_1_id = fields.Many2one("clinizone.lead_source", string="Level 1")
    level_2_id = fields.Many2one("clinizone.lead_source", string="Level 2")
