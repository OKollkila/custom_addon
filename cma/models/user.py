import os

from odoo import models, fields


class User(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    team_ids = fields.Many2many("clinizone.team", string="Teams")