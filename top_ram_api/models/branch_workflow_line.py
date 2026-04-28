# -*- coding: utf-8 -*-

from odoo import fields, models


class BranchWorkflowLine(models.Model):
    _name = 'clinizone.branch.workflow.line'
    _description = 'Branch workflow level and user assignment'

    branch_id = fields.Many2one(
        'clinizone.branch',
        string='Branch',
        required=True,
        ondelete='cascade',
    )
    workflow_level_id = fields.Many2one(
        'workflow.level',
        string='Workflow Level',
        required=True,
        ondelete='restrict',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
    )
