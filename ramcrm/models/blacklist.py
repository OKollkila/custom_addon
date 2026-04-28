from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Blacklist(models.Model):
    _name = 'clinizone.blacklist'
    _description = 'CliniZone Blacklist'

    phone = fields.Char("Phone", required=True)
    blacklist_reason = fields.Text("Blacklist Reason")

    @api.constrains('phone')
    def _check_phone(self):
        for record in self:
            if record.phone and self.env['clinizone.blacklist'].search_count([('phone', '=', record.phone)]) > 1:
                raise ValidationError("Phone number already exists in blacklist.")
