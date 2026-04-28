from odoo import models, fields


class Service(models.Model):
    _name = 'clinizone.service'
    _description = 'clinizone.service'

    name = fields.Char("Name", required=True)
    department_id = fields.Many2one('clinizone.department', string='Department', required=True)
    company_id = fields.Many2one('res.company', string='Company')
    company_id._auto = False
    company_ids = fields.Many2many(
        'res.company',
        'clinizone_service_company_rel',
        'service_id',
        'company_id',
        string='Companies',
        required=True
    )
