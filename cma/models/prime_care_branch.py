from odoo import models, fields


class PrimeCareBranch(models.Model):
    _name = 'clinizone.prime_care_branch'
    _description = 'clinizone.prime_care_branch'

    name = fields.Char("Name", required=True)
    branch_id = fields.Many2one("clinizone.branch", "Official Branch Name", required=True)