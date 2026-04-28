# -*- coding: utf-8 -*-

from odoo import fields, models


class Branch(models.Model):
    _inherit = 'clinizone.branch'

    workflow_line_ids = fields.One2many(
        'clinizone.branch.workflow.line',
        'branch_id',
        string='Workflow level / User',
    )
