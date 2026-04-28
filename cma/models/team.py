import os

from odoo import models, fields


class Team(models.Model):
    _name = 'clinizone.team'
    _description = 'clinizone.team'

    name = fields.Char("Name", required=True)
    member_ids = fields.Many2many("res.users")