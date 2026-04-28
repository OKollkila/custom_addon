from odoo import models, fields


class Department(models.Model):
    _inherit = 'clinizone.department'
    _sql_constraints = [('unique_clinizone_department_prime_care_code', 'UNIQUE(prime_care_code)', 'Prime Care Code must be unique')]

    prime_care_code = fields.Char(string='Prime Care Code', index=True)
